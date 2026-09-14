param([Parameter(Mandatory = $true)][string]$Wav)
# Dictation-based transcription of a WAV file, used to sanity-check vocoded lyrics.
Add-Type -AssemblyName System.Speech
$eng = New-Object System.Speech.Recognition.SpeechRecognitionEngine([System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
$eng.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
$eng.SetInputToWaveFile($Wav)
$eng.BabbleTimeout = [TimeSpan]::FromSeconds(0)
$eng.InitialSilenceTimeout = [TimeSpan]::FromSeconds(0)
$eng.EndSilenceTimeout = [TimeSpan]::FromSeconds(0.4)
$words = @()
while ($true) {
    try { $r = $eng.Recognize() } catch { break }
    if ($null -eq $r) { break }
    $words += $r.Text
}
$eng.Dispose()
Write-Output ($words -join ' / ')
