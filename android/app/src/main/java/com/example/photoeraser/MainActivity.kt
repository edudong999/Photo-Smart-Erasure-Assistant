package com.example.photoeraser

import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModelProvider
import com.example.photoeraser.data.api.ApiClient
import com.example.photoeraser.data.local.AppDatabase
import com.example.photoeraser.data.local.HistoryRepository
import com.example.photoeraser.data.local.InpaintRepository
import com.example.photoeraser.ui.*
import com.example.photoeraser.viewmodel.PhotoEraserViewModel
import com.example.photoeraser.viewmodel.PhotoEraserViewModelFactory
import com.example.photoeraser.viewmodel.Screen

class MainActivity : ComponentActivity() {

    private lateinit var viewModel: PhotoEraserViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize dependencies
        val database = AppDatabase.getInstance(applicationContext)
        val historyRepository = HistoryRepository(database.historyDao())
        val inpaintRepository = InpaintRepository(ApiClient.api, historyRepository)

        // Create ViewModel
        val viewModelFactory = PhotoEraserViewModelFactory(historyRepository, inpaintRepository)
        viewModel = ViewModelProvider(this, viewModelFactory)[PhotoEraserViewModel::class.java]

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val uiState by viewModel.uiState.collectAsState()

                    when (uiState.currentScreen) {
                        Screen.Home -> {
                            HomeScreen(
                                viewModel = viewModel,
                                onImageSelected = { uri, path ->
                                    viewModel.selectImage(uri, path)
                                    // Load bitmap
                                    val bitmap = BitmapFactory.decodeFile(path)
                                    bitmap?.let { viewModel.setOriginalBitmap(it) }
                                }
                            )
                        }

                        Screen.Editor -> {
                            EditorScreen(
                                viewModel = viewModel,
                                onBack = {
                                    viewModel.navigateTo(Screen.Home)
                                },
                                onSubmit = { imageFile, maskFile ->
                                    viewModel.submitInpaintTask(imageFile, maskFile)
                                }
                            )
                        }

                        Screen.Processing -> {
                            ProcessingScreen(
                                viewModel = viewModel,
                                onCancel = {
                                    viewModel.navigateTo(Screen.Editor)
                                }
                            )
                        }

                        Screen.Result -> {
                            ResultScreen(
                                viewModel = viewModel,
                                onBackToEditor = {
                                    viewModel.navigateTo(Screen.Editor)
                                },
                                onSaveSuccess = {
                                    Toast.makeText(
                                        this@MainActivity,
                                        getString(R.string.saved_successfully),
                                        Toast.LENGTH_SHORT
                                    ).show()
                                },
                                onReEdit = {
                                    viewModel.navigateTo(Screen.Editor)
                                }
                            )
                        }
                    }
                }
            }
        }

        // Observe processing status changes to navigate to result screen
        // This would be handled in the ViewModel, but we need to observe it here
        /* Ideally handled via LaunchedEffect in the screen composables */
    }
}
