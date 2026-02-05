package ru.neuroimagen.arviewer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.databinding.ActivityQrScannerBinding
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Activity для сканирования QR кодов с AR ссылками.
 * 
 * Поддерживаемые форматы ссылок:
 * - https://ar.neuroimagen.ru/view/{unique_id}
 * - arv://view/{unique_id}
 * - Прямой unique_id (UUID формат)
 */
class QrScannerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityQrScannerBinding
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var barcodeScanner: BarcodeScanner
    
    private var isProcessing = false

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startCamera()
        } else {
            Toast.makeText(this, getString(R.string.camera_permission_required), Toast.LENGTH_LONG).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityQrScannerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()
        
        val options = BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
        barcodeScanner = BarcodeScanning.getClient(options)

        binding.buttonClose.setOnClickListener { finish() }

        if (hasCameraPermission()) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        barcodeScanner.close()
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(binding.previewView.surfaceProvider)
                }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    cameraSelector,
                    preview,
                    imageAnalyzer
                )
            } catch (e: Exception) {
                Log.e(TAG, "Ошибка привязки камеры", e)
                Toast.makeText(this, getString(R.string.camera_error), Toast.LENGTH_LONG).show()
                finish()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun processImage(imageProxy: ImageProxy) {
        if (isProcessing) {
            imageProxy.close()
            return
        }

        val mediaImage = imageProxy.image
        if (mediaImage == null) {
            imageProxy.close()
            return
        }

        val inputImage = InputImage.fromMediaImage(
            mediaImage,
            imageProxy.imageInfo.rotationDegrees
        )

        barcodeScanner.process(inputImage)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    barcode.rawValue?.let { value ->
                        val uniqueId = parseQrContent(value)
                        if (uniqueId != null) {
                            handleScannedCode(uniqueId)
                            return@addOnSuccessListener
                        }
                    }
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Ошибка сканирования", e)
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

    /**
     * Парсит содержимое QR кода и извлекает unique_id.
     * 
     * @param content содержимое QR кода (URL или UUID)
     * @return unique_id или null если формат не распознан
     */
    private fun parseQrContent(content: String): String? {
        // Проверяем прямой UUID формат
        if (UUID_REGEX.matches(content)) {
            return content
        }

        // Пробуем распарсить как URL
        return try {
            val uri = Uri.parse(content)
            when {
                // https://ar.neuroimagen.ru/view/{unique_id}
                uri.scheme in listOf("https", "http") && uri.host == "ar.neuroimagen.ru" -> {
                    uri.pathSegments.getOrNull(1)?.takeIf { UUID_REGEX.matches(it) }
                }
                // arv://view/{unique_id}
                uri.scheme == "arv" && uri.host == "view" -> {
                    uri.pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
                        ?: uri.path?.trimStart('/')?.takeIf { UUID_REGEX.matches(it) }
                }
                else -> null
            }
        } catch (e: Exception) {
            Log.w(TAG, "Не удалось распарсить QR: $content", e)
            null
        }
    }

    private fun handleScannedCode(uniqueId: String) {
        if (isProcessing) return
        isProcessing = true

        runOnUiThread {
            binding.panelProcessing.visibility = View.VISIBLE
        }

        // Возвращаем результат в MainActivity
        val resultIntent = Intent().apply {
            putExtra(EXTRA_UNIQUE_ID, uniqueId)
        }
        setResult(RESULT_OK, resultIntent)
        finish()
    }

    companion object {
        private const val TAG = "QrScannerActivity"
        const val EXTRA_UNIQUE_ID = "extra_unique_id"
        
        private val UUID_REGEX = Regex(
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )
    }
}
