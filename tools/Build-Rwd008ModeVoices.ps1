$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$taskVoiceRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets\rwd008-mode-voices'
[System.IO.Directory]::CreateDirectory($taskVoiceRoot) | Out-Null
$taskSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $taskSynth.SelectVoice('Microsoft Mark')
    $taskSynth.Rate = 1
    $taskSynth.Volume = 100
    foreach ($taskMode in @('Easy', 'Normal', 'Hard')) {
        $taskVoicePath = Join-Path $taskVoiceRoot ($taskMode.ToLowerInvariant() + '-mode.wav')
        if (Test-Path -LiteralPath $taskVoicePath) { throw "Voice already exists: $taskVoicePath" }
        $taskSynth.SetOutputToWaveFile($taskVoicePath)
        $taskSynth.Speak($taskMode + ' mode!')
        $taskSynth.SetOutputToNull()
        Get-Item -LiteralPath $taskVoicePath | Select-Object Name,Length
    }
} finally { $taskSynth.Dispose() }
