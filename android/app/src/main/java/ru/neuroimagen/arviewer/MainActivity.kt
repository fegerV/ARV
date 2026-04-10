package ru.neuroimagen.arviewer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.text.HtmlCompat
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
import ru.neuroimagen.arviewer.databinding.DialogInfoOverlayBinding
import ru.neuroimagen.arviewer.ui.MainViewModel
import ru.neuroimagen.arviewer.ui.ViewerErrorMessages
import dagger.hilt.android.AndroidEntryPoint
import ru.neuroimagen.arviewer.util.UniqueIdParser
import android.text.method.LinkMovementMethod

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
                submitResolvedUniqueId(uniqueId, fromQrScan = true)
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

        binding.buttonScanQr.setOnClickListener { openQrScanner() }
        binding.buttonTryDemo.setOnClickListener { openDemoMode() }
        binding.buttonOpenFromFile.setOnClickListener { pickImageLauncher.launch("image/*") }
        binding.buttonHowItWorks.setOnClickListener {
            showInfoDialog(R.string.dialog_how_to_use_title, R.string.dialog_how_to_use_body)
        }
        binding.buttonCheckArSupport.setOnClickListener { openArCorePlayStore() }
        binding.buttonOrderAr.setOnClickListener { openOrderPage() }
        binding.buttonRetry.setOnClickListener { viewModel.retry() }
        binding.textPrivacy.setOnClickListener { openPrivacyPolicy() }
        binding.textAbout.setOnClickListener { showInfoDialog(R.string.dialog_about_title, R.string.dialog_about_body) }
        binding.textSupport.setOnClickListener { showInfoDialog(R.string.dialog_support_title, R.string.dialog_support_body) }

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
                submitResolvedUniqueId(uniqueId, fromQrScan = true)
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
            submitResolvedUniqueId(uniqueId)
        }
    }

    // ── Open viewer ──────────────────────────────────────────────────

    private fun openDemoMode() {
        if (!ArSessionHelper.isArCoreSupported(this)) {
            showDeviceNotSupportedPanel("demo")
            return
        }
        startActivity(Intent(this, DemoIntroActivity::class.java))
    }

    private fun openPrivacyPolicy() {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(getString(R.string.privacy_url))))
    }

    private fun openOrderPage() {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://vertex-art.ru/ar")))
    }

    private fun showInfoDialog(titleRes: Int, bodyRes: Int) {
        val dialogBinding = DialogInfoOverlayBinding.inflate(layoutInflater)
        val dialog = AlertDialog.Builder(this, androidx.appcompat.R.style.Theme_AppCompat_Dialog)
            .setView(dialogBinding.root)
            .create()

        dialogBinding.textDialogTitle.setText(titleRes)
        dialogBinding.textDialogBody.text = HtmlCompat.fromHtml(
            getString(bodyRes),
            HtmlCompat.FROM_HTML_MODE_LEGACY,
        )
        dialogBinding.textDialogBody.movementMethod = LinkMovementMethod.getInstance()
        dialogBinding.buttonCloseDialog.setOnClickListener { dialog.dismiss() }

        dialog.setCanceledOnTouchOutside(true)
        dialog.window?.apply {
            setBackgroundDrawableResource(android.R.color.transparent)
            setDimAmount(0.8f)
            setGravity(Gravity.CENTER)
        }

        dialog.show()
        dialog.window?.setLayout(
            (resources.displayMetrics.widthPixels * 0.9f).toInt(),
            ViewGroup.LayoutParams.WRAP_CONTENT,
        )
    }

    /**
     * @param fromQrScan true when user just scanned a QR (camera or gallery) — skips manifest cache so the correct content loads.
     */
    private fun openViewer(uniqueId: String, fromQrScan: Boolean = false) {
        // Pre-flight: check ARCore support BEFORE heavy network loading
        if (!ArSessionHelper.isArCoreSupported(this)) {
            showDeviceNotSupportedPanel(uniqueId)
            return
        }
        viewModel.loadManifest(uniqueId, forceRefresh = fromQrScan)
    }

    private fun submitResolvedUniqueId(
        uniqueId: String,
        fromQrScan: Boolean = false,
        updateInputField: Boolean = true,
    ) {
        openViewer(uniqueId, fromQrScan = fromQrScan)
    }

    private fun parseInputUniqueId(input: String): String? {
        val uniqueId = UniqueIdParser.extractFromInput(input)
        if (uniqueId != null) {
            return uniqueId
        }

        val errorMsg = if (UniqueIdParser.looksLikeUrl(input)) {
            getString(R.string.error_invalid_link_format)
        } else {
            getString(R.string.error_invalid_unique_id)
        }
        Toast.makeText(this, errorMsg, Toast.LENGTH_LONG).show()
        return null
    }

    private fun showDeviceNotSupportedPanel(uniqueId: String) {
        viewModel.resetToInput()
        binding.panelMain.visibility = View.GONE
        binding.panelLoading.visibility = View.GONE
        binding.panelError.visibility = View.VISIBLE
        binding.textError.text = getString(R.string.error_device_not_supported)
        binding.buttonRetry.text = getString(R.string.button_check_arcore_again)
        binding.buttonRetry.visibility = View.VISIBLE
        binding.buttonOpenDeviceList.visibility = View.VISIBLE
        binding.buttonRetry.setOnClickListener {
            if (ArSessionHelper.isArCoreSupported(this)) {
                binding.buttonOpenDeviceList.visibility = View.GONE
                if (uniqueId == "demo") {
                    showMainPanel()
                    openDemoMode()
                } else {
                    submitResolvedUniqueId(uniqueId, updateInputField = false)
                }
            }
        }
        binding.buttonOpenDeviceList.setOnClickListener { openArCoreDeviceListUrl() }
    }

    private fun openArCoreDeviceListUrl() {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://developers.google.com/ar/devices")))
    }

    /** Open Play Store ARCore page — shows "supported" or "not supported" for the device. */
    private fun openArCorePlayStore() {
        val marketUri = Uri.parse("market://details?id=com.google.ar.core")
        val webUri = Uri.parse("https://play.google.com/store/apps/details?id=com.google.ar.core")
        val intent = Intent(Intent.ACTION_VIEW, marketUri).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            startActivity(intent)
        } catch (_: Exception) {
            startActivity(Intent(Intent.ACTION_VIEW, webUri))
        }
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
        binding.buttonRetry.text = getString(R.string.retry)
        binding.buttonRetry.visibility = if (retryable) View.VISIBLE else View.GONE
        binding.buttonRetry.setOnClickListener { viewModel.retry() }
        binding.buttonOpenDeviceList.visibility = View.GONE
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}
