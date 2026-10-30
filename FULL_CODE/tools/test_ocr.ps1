# Test script for Windows Native OCR
param([string]$ImagePath)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

if (-not (Test-Path $ImagePath)) {
    Write-Output "Image file not found: $ImagePath"
    exit 1
}

$fullPath = (Resolve-Path $ImagePath).Path
$storageFile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)) ([Windows.Storage.StorageFile])
$stream = Await ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$lang = New-Object Windows.Globalization.Language("en-US")
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}

$ocrResult = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
Write-Output $ocrResult.Text
