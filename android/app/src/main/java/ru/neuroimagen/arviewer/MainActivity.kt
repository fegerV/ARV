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
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.ar.ArSessionHelper
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.databinding.ActivityMainBinding
import ru.neuroimagen.arviewer.ui.MainViewModel
import ru.neuroimagen.arviewer.ui.ViewerErrorMessages
import dagger.hilt.android.AndroidEntryPoint
import ru.neuroimagen.arviewer.util.UniqueIdParser

/**
 * Main screen: QR scanning (primary action), QR from gallery, and manual unique_id input.
 * Requests all required permissions (camera, microphone) at startup.
 *
 * Also serves as the LAUNCHER activity with SplashScreen API (replaces SplashActivity).
 * Business logic (manifest loading, retry) is delegated to [MainViewModel].
 */
@AndroidEntryPoint
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: MainViewModel by viewModels()

    // ── Permission request at startup ────────────────────────────────

    private val permissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val cameraGranted = results[Manifest.permission.CAMERA] == true
        if (!cameraGranted) {
            Toast.makeText(this, R.string.error_camera_required, Toast.LENGTH_LONG).show()
        }
    }

    private val qrScannerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val uniqueId = result.data?.getStringExtra(QrScannerActivity.EXTRA_UNIQUE_ID)
            if (!uniqueId.isNullOrBlank()) {
                binding.editUniqueId.setText(uniqueId)
                openViewer(uniqueId)
            }
        }
    }

    /**
     * Pick an image from gallery to decode a QR code from it.
     */
    private val pickImageLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { decodeQrFromImage(it) }
    }

    // ── Lifecycle ────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.buttonOpen.setOnClickListener { onOpenClicked() }
        binding.buttonScanQr.setOnClickListener { openQrScanner() }
        binding.buttonOpenFromFile.setOnClickListener { pickImageLauncher.launch("image/*") }
        binding.buttonRetry.setOnClickListener { viewModel.retry() }

        observeUiState()
        requestRequiredPermissions()
        handleIntent(intent)
    }

    // ── State observation ────────────────────────────────────────────

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    when (state) {
                        is MainViewModel.UiState.Input -> showMainPanel()
                        is MainViewModel.UiState.Loading -> showLoadingPanel()
                        is MainViewModel.UiState.Error -> {
                            val message = buildErrorMessage(state.viewerError, state.throwable)
                            showErrorPanel(message, state.retryable)
                        }
                        is MainViewModel.UiState.NavigateToAr -> {
                            navigateToArViewer(state.manifestJson, state.uniqueId)
                            viewModel.onNavigated()
                        }
                    }
                }
            }
        }
    }

    // ── Permissions ──────────────────────────────────────────────────

    private fun requestRequiredPermissions() {
        val needed = mutableListOf<String>()
        if (!hasPermission(Manifest.permission.CAMERA)) {
            needed.add(Manifest.permission.CAMERA)
        }
        if (!hasPermission(Manifest.permission.RECORD_AUDIO)) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (needed.isNotEmpty()) {
            permissionsLauncher.launch(needed.toTypedArray())
        }
    }

    private fun hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    // ── QR scanner ───────────────────────────────────────────────────

    private fun openQrScanner() {
        val intent = Intent(this, QrScannerActivity::class.java)
        qrScannerLauncher.launch(intent)
    }

    // ── QR from gallery image ────────────────────────────────────────

    /**
     * Decode a QR code from a picked gallery image using ML Kit.
     */
    private fun decodeQrFromImage(imageUri: Uri) {
        viewModel.setLoading()
        lifecycleScope.launch {
            val uniqueId = withContext(Dispatchers.IO) {
                scanBarcodeFromImage(imageUri)
            }
            if (uniqueId != null) {
                binding.editUniqueId.setText(uniqueId)
                viewModel.loadManifest(uniqueId)
            } else {
                viewModel.resetToInput()
                Toast.makeText(
                    this@MainActivity,
                    R.string.qr_not_found_in_image,
                    Toast.LENGTH_LONG,
                ).show()
            }
        }
    }

    /**
     * Use ML Kit barcode scanner to find a QR code in the given image.
     *
     * @return extracted unique_id if a valid AR QR code is found, null otherwise
     */
    private fun scanBarcodeFromImage(imageUri: Uri): String? {
        return try {
            val image = InputImage.fromFilePath(this, imageUri)
            val options = BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
            val scanner = BarcodeScanning.getClient(options)
            val barcodes = Tasks.await(scanner.process(image))
            scanner.close()
            barcodes.firstNotNullOfOrNull { barcode ->
                barcode.rawValue?.let { UniqueIdParser.extractFromInput(it) }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode QR from image", e)
            null
        }
    }

    // ── Intent handling ──────────────────────────────────────────────

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val data: Uri = intent?.data ?: return
        val uniqueId = UniqueIdParser.parseFromUri(data) ?: return
        if (uniqueId.isNotBlank()) {
            binding.editUniqueId.setText(uniqueId)
            openViewer(uniqueId)
        }
    }

    // ── Open viewer ──────────────────────────────────────────────────

    private fun onOpenClicked() {
        val input = binding.editUniqueId.text.toString().trim()
        if (input.isEmpty()) {
            Toast.makeText(this, getString(R.string.enter_unique_id), Toast.LENGTH_SHORT).show()
            return
        }
        val uniqueId = UniqueIdParser.extractFromInput(input)
        if (uniqueId == null) {
            val errorMsg = if (UniqueIdParser.looksLikeUrl(input)) {
                getString(R.string.error_invalid_link_format)
            } else {
                getString(R.string.error_invalid_unique_id)
            }
            Toast.makeText(this, errorMsg, Toast.LENGTH_LONG).show()
            return
        }
        openViewer(uniqueId)
    }

    private fun openViewer(uniqueId: String) {
        // Pre-flight: check ARCore support BEFORE heavy network loading
        if (!ArSessionHelper.isArCoreSupported(this)) {
            viewModel.resetToInput()
            Toast.makeText(this, R.string.error_device_not_supported, Toast.LENGTH_LONG).show()
            return
        }
        viewModel.loadManifest(uniqueId)
    }

    private fun navigateToArViewer(manifestJson: String, uniqueId: String) {
        startActivity(
            Intent(this, ArViewerActivity::class.java).apply {
                putExtra(ArViewerActivity.EXTRA_MANIFEST_JSON, manifestJson)
                putExtra(ArViewerActivity.EXTRA_UNIQUE_ID, uniqueId)
            },
        )
    }

    /**
     * Build a human-readable error message from a [ViewerError] or generic throwable.
     */
    private fun buildErrorMessage(error: ViewerError?, throwable: Throwable): String {
        return when (error) {
            is ViewerError.Server -> getString(R.string.error_server, error.code)
            is ViewerError.Network -> {
                val base = getString(R.string.error_network)
                val detail = if (!error.msg.isNullOrBlank()) "\n(${error.msg})" else ""
                val hint = getString(R.string.error_network_hint)
                "$base$detail\n\n$hint"
            }
            is ViewerError -> getString(ViewerErrorMessages.getMessageResId(error))
            else -> getString(R.string.error_unknown)
        }
    }

    // ── Panel switching ──────────────────────────────────────────────

    private fun showMainPanel() {
        binding.panelMain.visibility = View.VISIBLE
        binding.panelLoading.visibility = View.GONE
        binding.panelError.visibility = View.GONE
    }

    private fun showLoadingPanel() {
        binding.panelMain.visibility = View.GONE
        binding.panelLoading.visibility = View.VISIBLE
        binding.panelError.visibility = View.GONE
    }

    /**
     * Show the error panel with a message.
     *
     * @param message  User-facing error text.
     * @param retryable  If `false`, the "Retry" button is hidden (permanent errors).
     */
    private fun showErrorPanel(message: String, retryable: Boolean = true) {
        binding.panelMain.visibility = View.GONE
        binding.panelLoading.visibility = View.GONE
        binding.panelError.visibility = View.VISIBLE
        binding.textError.text = message
        binding.buttonRetry.visibility = if (retryable) View.VISIBLE else View.GONE
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}
