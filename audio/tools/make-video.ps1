param(
    [Parameter(Mandatory=$true)][string]$BeforeImage,
    [Parameter(Mandatory=$true)][string]$BeforeAudio,
    [Parameter(Mandatory=$true)][string]$AfterImage,
    [Parameter(Mandatory=$true)][string]$AfterAudio,
    [Parameter(Mandatory=$true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSEdition -ne 'Desktop') {
    throw 'Run this script with Windows PowerShell 5.1 (powershell.exe).'
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Media.Editing.MediaClip,Windows.Media.Editing,ContentType=WindowsRuntime]
$null = [Windows.Media.Editing.MediaComposition,Windows.Media.Editing,ContentType=WindowsRuntime]
$null = [Windows.Media.Editing.BackgroundAudioTrack,Windows.Media.Editing,ContentType=WindowsRuntime]
$null = [Windows.Media.Editing.MediaTrimmingPreference,Windows.Media.Editing,ContentType=WindowsRuntime]
$null = [Windows.Media.MediaProperties.MediaEncodingProfile,Windows.Media.MediaProperties,ContentType=WindowsRuntime]
$null = [Windows.Media.Transcoding.TranscodeFailureReason,Windows.Media.Transcoding,ContentType=WindowsRuntime]

$taskBridges = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1
}
$asyncBridge = $taskBridges | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }
$progressBridge = $taskBridges | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2' }

function Wait-Result($operation, [Type]$resultType) {
    $task = $asyncBridge.MakeGenericMethod($resultType).Invoke($null, @($operation))
    return $task.GetAwaiter().GetResult()
}

function Get-MediaFile([string]$Path) {
    $fullPath = (Resolve-Path -LiteralPath $Path).ProviderPath
    return Wait-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)) ([Windows.Storage.StorageFile])
}

$destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$stage = Join-Path ([IO.Path]::GetTempPath()) ('speech-compare-' + [guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stage)
$stagedBeforeImage = Join-Path $stage 'before.png'
$stagedBeforeAudio = Join-Path $stage 'before.wav'
$stagedAfterImage = Join-Path $stage 'after.png'
$stagedAfterAudio = Join-Path $stage 'after.wav'
$tempVideo = Join-Path $stage 'comparison.mp4'
try {
    # Media Foundation may open media under a separate process identity.
    # Stage all five files together in the current process's temporary folder.
    [IO.File]::Copy((Resolve-Path -LiteralPath $BeforeImage).ProviderPath, $stagedBeforeImage)
    [IO.File]::Copy((Resolve-Path -LiteralPath $BeforeAudio).ProviderPath, $stagedBeforeAudio)
    [IO.File]::Copy((Resolve-Path -LiteralPath $AfterImage).ProviderPath, $stagedAfterImage)
    [IO.File]::Copy((Resolve-Path -LiteralPath $AfterAudio).ProviderPath, $stagedAfterAudio)
    $composition = [Windows.Media.Editing.MediaComposition]::new()
    $clipAppend = [System.Collections.Generic.ICollection[Windows.Media.Editing.MediaClip]].GetMethod('Add')
    $audioAppend = [System.Collections.Generic.ICollection[Windows.Media.Editing.BackgroundAudioTrack]].GetMethod('Add')
    foreach ($pair in @(@($stagedBeforeImage,$stagedBeforeAudio), @($stagedAfterImage,$stagedAfterAudio))) {
        $voiceFile = Get-MediaFile $pair[1]
        $track = Wait-Result ([Windows.Media.Editing.BackgroundAudioTrack]::CreateFromFileAsync($voiceFile)) ([Windows.Media.Editing.BackgroundAudioTrack])
        $imageFile = Get-MediaFile $pair[0]
        $still = Wait-Result ([Windows.Media.Editing.MediaClip]::CreateFromImageFileAsync($imageFile, $track.OriginalDuration)) ([Windows.Media.Editing.MediaClip])
        $track.Delay = $composition.Duration
        $null = $clipAppend.Invoke($composition.Clips, @($still))
        $null = $audioAppend.Invoke($composition.BackgroundAudioTracks, @($track))
    }

    $profile = [Windows.Media.MediaProperties.MediaEncodingProfile]::CreateMp4('HD720p')
    $profile.Video.Width = 720
    $profile.Video.Height = 720
    $profile.Video.Bitrate = 650000
    $profile.Video.FrameRate.Numerator = 15
    $profile.Video.FrameRate.Denominator = 1
    $profile.Audio.Bitrate = 128000


    [IO.File]::WriteAllBytes($tempVideo, [byte[]]@())
    $targetFile = Get-MediaFile $tempVideo
    $operation = $composition.RenderToFileAsync($targetFile, [Windows.Media.Editing.MediaTrimmingPreference]::Precise, $profile)
    $task = $progressBridge.MakeGenericMethod([Windows.Media.Transcoding.TranscodeFailureReason], [double]).Invoke($null, @($operation))
    $result = $task.GetAwaiter().GetResult()
    if ($result.ToString() -ne 'None') { throw "Video encoding failed ($result)." }
    [IO.File]::Copy($tempVideo, $destination, $true)
} finally {
    $composition = $null
    $track = $null
    $still = $null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    foreach ($file in @($tempVideo,$stagedBeforeImage,$stagedBeforeAudio,$stagedAfterImage,$stagedAfterAudio)) {
        if ([IO.File]::Exists($file)) { [IO.File]::Delete($file) }
    }
    [IO.Directory]::Delete($stage)
}
