package ru.neuroimagen.arviewer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import dagger.hilt.android.AndroidEntryPoint
import ru.neuroimagen.arviewer.databinding.ActivityQrScannerBinding
import ru.neuroimagen.arviewer.util.UniqueIdParser
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

@AndroidEntryPoint
class QrScannerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityQrScannerBinding
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var barcodeScanner: BarcodeScanner

    private var camera: Camera? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageAnalyzer: ImageAnalysis? = null

    private var isProcessing = false
    private var isFlashEnabled = false
    private var scannerActive = false
    private var lastInvalidQrShownTime = 0L
    private var lastInvalidQrContent: String? = null

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
        binding.buttonToggleFlash.setOnClickListener { toggleFlash() }
        updateFlashButton()

        if (hasCameraPermission()) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    override fun onDestroy() {
        scannerActive = false
        imageAnalyzer?.clearAnalyzer()
        cameraProvider?.unbindAll()
        super.onDestroy()
        cameraExecutor.shutdown()
        runCatching { barcodeScanner.close() }
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun startCamera() {
        scannerActive = true
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val provider = cameraProviderFuture.get()
            cameraProvider = provider

            val preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(binding.previewView.surfaceProvider)
                }

            imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                provider.unbindAll()
                camera = provider.bindToLifecycle(
                    this,
                    cameraSelector,
                    preview,
                    imageAnalyzer
                )
                updateFlashButton()
            } catch (e: Exception) {
                Log.e(TAG, "Error binding camera", e)
                Toast.makeText(this, getString(R.string.camera_error), Toast.LENGTH_LONG).show()
                finish()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun processImage(imageProxy: ImageProxy) {
        if (!scannerActive || isProcessing || isFinishing || isDestroyed) {
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

        try {
            barcodeScanner.process(inputImage)
                .addOnSuccessListener { barcodes ->
                    if (!scannerActive || isFinishing || isDestroyed) return@addOnSuccessListener

                    for (barcode in barcodes) {
                        val value = barcode.rawValue ?: continue
                        val uniqueId = parseQrContent(value)
                        if (uniqueId != null) {
                            handleScannedCode(uniqueId)
                            return@addOnSuccessListener
                        }

                        val now = System.currentTimeMillis()
                        if (value != lastInvalidQrContent || now - lastInvalidQrShownTime > 3000) {
                            lastInvalidQrContent = value
                            lastInvalidQrShownTime = now
                            showInvalidQrMessage(value)
                        }
                    }
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Error scanning QR", e)
                }
                .addOnCompleteListener {
                    imageProxy.close()
                }
        } catch (e: Exception) {
            Log.e(TAG, "Scanner processing failed", e)
            imageProxy.close()
        }
    }

    private fun parseQrContent(content: String): String? {
        return UniqueIdParser.extractFromInput(content)
    }

    private fun showInvalidQrMessage(scannedContent: String) {
        runOnUiThread {
            if (isFinishing || isDestroyed) return@runOnUiThread
            val message = getString(R.string.error_qr_not_recognized) + "\n$scannedContent"
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }
    }

    private fun handleScannedCode(uniqueId: String) {
        if (isProcessing) return
        isProcessing = true
        scannerActive = false

        runOnUiThread {
            if (isFinishing || isDestroyed) return@runOnUiThread
            binding.panelProcessing.visibility = View.VISIBLE
        }

        val resultIntent = Intent().apply {
            putExtra(EXTRA_UNIQUE_ID, uniqueId)
        }
        setResult(RESULT_OK, resultIntent)
        finish()
    }

    private fun toggleFlash() {
        val boundCamera = camera ?: return
        if (!boundCamera.cameraInfo.hasFlashUnit()) {
            Toast.makeText(this, getString(R.string.flash_not_available), Toast.LENGTH_SHORT).show()
            binding.buttonToggleFlash.isEnabled = false
            return
        }

        isFlashEnabled = !isFlashEnabled
        boundCamera.cameraControl.enableTorch(isFlashEnabled)
        updateFlashButton()
    }

    private fun updateFlashButton() {
        val hasFlashUnit = camera?.cameraInfo?.hasFlashUnit() == true
        binding.buttonToggleFlash.isEnabled = hasFlashUnit
        binding.buttonToggleFlash.alpha = if (hasFlashUnit) 1f else 0.6f
        binding.buttonToggleFlash.text = getString(
            if (isFlashEnabled) R.string.toggle_flash_off else R.string.toggle_flash_on
        )
    }

    companion object {
        private const val TAG = "QrScannerActivity"
        const val EXTRA_UNIQUE_ID = "extra_unique_id"
    }
}
