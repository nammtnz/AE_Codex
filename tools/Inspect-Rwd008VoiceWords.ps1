$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$taskInfo = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Select-Object -First 1
$taskRecognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($taskInfo)
try {
    $taskRecognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $taskRecognizer.SetInputToWaveFile('C:\Users\nguye\AppData\Local\Temp\rwd008-difficulty-asr.wav')
    for ($taskI=0; $taskI -lt 10; $taskI++) {
        $taskRecognized = $taskRecognizer.Recognize()
        if ($null -eq $taskRecognized) { break }
        [pscustomobject]@{Text=$taskRecognized.Text;Confidence=$taskRecognized.Confidence;Start=$taskRecognized.Audio.AudioPosition.TotalSeconds;Duration=$taskRecognized.Audio.Duration.TotalSeconds}
    }
} finally { $taskRecognizer.Dispose() }
