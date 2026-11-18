param(
    [string]$Python = 'python',
    [string]$OutputDirectory = $PSScriptRoot,
    [switch]$Video
)
$ErrorActionPreference = 'Stop'
$out = [IO.Directory]::CreateDirectory($OutputDirectory).FullName
$tempDir = [IO.Directory]::CreateDirectory((Join-Path ([IO.Path]::GetTempPath()) ('voice-demo-' + [guid]::NewGuid()))).FullName
try {
    $raw = Join-Path $PSScriptRoot 'denis.wav'
    & $Python "$PSScriptRoot\tools\render.py" $raw $out $tempDir
    if ($LASTEXITCODE) { throw 'Audio rendering failed.' }
    if ($Video) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\tools\make-video.ps1" -BeforeImage "$tempDir\before.png" -BeforeAudio "$out\before.wav" -AfterImage "$tempDir\after.png" -AfterAudio "$out\after.wav" -OutputPath "$out\comparison.mp4"
        if ($LASTEXITCODE) { throw 'Video rendering failed.' }
    }
} finally {
    foreach ($name in @('before.png', 'after.png')) {
        [IO.File]::Delete((Join-Path $tempDir $name))
    }
    [IO.Directory]::Delete($tempDir, $false)
}
