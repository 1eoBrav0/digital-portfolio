param(
    [string]$Python = 'python',
    [string]$OutputDirectory = $PSScriptRoot,
    [switch]$Video
)
$ErrorActionPreference = 'Stop'
$out = [IO.Directory]::CreateDirectory($OutputDirectory).FullName
$tempDir = [IO.Directory]::CreateDirectory((Join-Path ([IO.Path]::GetTempPath()) ('voice-demo-' + [guid]::NewGuid()))).FullName
$text = 'Утром я вышла на пустую набережную. Вода ещё спала. И только где-то за мостом перекликались первые трамваи.'
try {
    $raw = Join-Path $tempDir 'voice.wav'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\tools\voice.ps1" -OutputPath $raw -SpokenText $text
    if ($LASTEXITCODE) { throw 'Speech synthesis failed.' }
    & $Python "$PSScriptRoot\tools\render.py" $raw $out $tempDir
    if ($LASTEXITCODE) { throw 'Audio rendering failed.' }
    if ($Video) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\tools\make-video.ps1" -BeforeImage "$tempDir\before.png" -BeforeAudio "$out\before.wav" -AfterImage "$tempDir\after.png" -AfterAudio "$out\after.wav" -OutputPath "$out\comparison.mp4"
        if ($LASTEXITCODE) { throw 'Video rendering failed.' }
    }
} finally {
    foreach ($name in @('voice.wav', 'before.png', 'after.png')) {
        [IO.File]::Delete((Join-Path $tempDir $name))
    }
    [IO.Directory]::Delete($tempDir, $false)
}
