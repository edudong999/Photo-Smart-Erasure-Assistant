package com.example.photoeraser.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.example.photoeraser.R
import com.example.photoeraser.viewmodel.PhotoEraserViewModel
import java.io.File
import java.io.FileOutputStream

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditorScreen(
    viewModel: PhotoEraserViewModel,
    onBack: () -> Unit,
    onSubmit: (File, File) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var originalBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var maskBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var showError by remember { mutableStateOf<String?>(null) }

    // Load original bitmap
    LaunchedEffect(uiState.selectedImagePath) {
        uiState.selectedImagePath?.let { path ->
            originalBitmap = BitmapFactory.decodeFile(path)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("画笔涂抹") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = {
                        // Undo - would need to track path history
                    }) {
                        Icon(Icons.Default.Undo, contentDescription = stringResource(R.string.undo))
                    }
                    IconButton(onClick = {
                        // Redo
                    }) {
                        Icon(Icons.Default.Redo, contentDescription = stringResource(R.string.redo))
                    }
                    IconButton(onClick = {
                        // Reset - clear mask
                        maskBitmap = null
                    }) {
                        Icon(Icons.Default.Refresh, contentDescription = stringResource(R.string.reset))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        },
        bottomBar = {
            EditorBottomBar(
                brushSize = uiState.brushSize,
                onBrushSizeChange = { viewModel.setBrushSize(it) },
                onSubmit = {
                    if (maskBitmap == null) {
                        showError = "请先涂抹要消除的区域"
                    } else {
                        val imageFile = File(uiState.selectedImagePath!!)
                        val maskFile = createMaskFile(maskBitmap!!)
                        onSubmit(imageFile, maskFile)
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Canvas area
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(8.dp)
            ) {
                originalBitmap?.let { bitmap ->
                    BrushView(
                        originalBitmap = bitmap,
                        brushSize = uiState.brushSize,
                        onMaskGenerated = { mask ->
                            maskBitmap = mask
                        },
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }

            // Error message
            showError?.let { error ->
                Snackbar(
                    modifier = Modifier.padding(8.dp),
                    action = {
                        TextButton(onClick = { showError = null }) {
                            Text("关闭")
                        }
                    }
                ) {
                    Text(error)
                }
            }
        }
    }

    // Show error snackbar
    LaunchedEffect(showError) {
        if (showError != null) {
            kotlinx.coroutines.delay(3000)
            showError = null
        }
    }
}

@Composable
fun EditorBottomBar(
    brushSize: Float,
    onBrushSizeChange: (Float) -> Unit,
    onSubmit: () -> Unit
) {
    Surface(
        tonalElevation = 4.dp,
        shadowElevation = 8.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Brush size slider
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.Brush,
                    contentDescription = null,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.brush_size),
                    style = MaterialTheme.typography.bodyMedium
                )
                Spacer(modifier = Modifier.width(16.dp))
                Slider(
                    value = brushSize,
                    onValueChange = onBrushSizeChange,
                    valueRange = 10f..100f,
                    modifier = Modifier.weight(1f)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "${brushSize.toInt()}px",
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Submit button
            Button(
                onClick = onSubmit,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(Icons.Default.AutoFixHigh, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.start_erasing),
                    style = MaterialTheme.typography.titleMedium
                )
            }
        }
    }
}

private fun createMaskFile(maskBitmap: Bitmap): File {
    val tempFile = File.createTempFile("mask_", ".png")
    FileOutputStream(tempFile).use { out ->
        maskBitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
    }
    return tempFile
}
