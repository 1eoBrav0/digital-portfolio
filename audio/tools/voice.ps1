param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [Parameter(Mandatory = $true)][string]$SpokenText,
    [string]$VoiceName = 'Microsoft Irina'
)
# Run with Windows PowerShell 5.1 and a locally installed Russian OneCore voice.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$voiceType = [Windows.Media.SpeechSynthesis.SpeechSynthesizer,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime]
$streamType = [Windows.Media.SpeechSynthesis.SpeechSynthesisStream,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime]
$voice = $voiceType::AllVoices | Where-Object DisplayName -eq $VoiceName | Select-Object -First 1
if (-not $voice) { throw "Install the Windows text-to-speech voice $VoiceName to generate this example." }
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
try {
    $synth.Voice = $voice
    $operation = $synth.SynthesizeTextToStreamAsync($SpokenText)
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    $task = $asTask.MakeGenericMethod($streamType).Invoke($null, @($operation))
    $task.Wait()
    $source = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($task.Result)
    try {
        $target = [IO.File]::Create($OutputPath)
        try { $source.CopyTo($target) } finally { $target.Dispose() }
    } finally { $source.Dispose() }
} finally { $synth.Dispose() }