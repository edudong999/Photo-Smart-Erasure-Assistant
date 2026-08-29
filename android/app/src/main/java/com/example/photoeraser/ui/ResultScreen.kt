package com.example.photoeraser.ui

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.photoeraser.R
import com.example.photoeraser.viewmodel.PhotoEraserViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultScreen(
    viewModel: PhotoEraserViewModel,
    onBackToEditor: () -> Unit,
    onSaveSuccess: () -> Unit,
    onReEdit: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var beforeBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var afterBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var isSaving by remember { mutableStateOf(false) }
    var saveSuccess by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Load bitmaps
    LaunchedEffect(uiState.selectedImagePath, uiState.taskId) {
        uiState.selectedImagePath?.let { path ->
            beforeBitmap = BitmapFactory.decodeFile(path)
        }

        // Download result image
        uiState.taskId?.let { taskId ->
            viewModel.downloadAndLoadResult(context, taskId)
        }
    }

    // Load result bitmap when available
    LaunchedEffect(uiState.resultBitmap) {
        uiState.resultBitmap?.let {
            afterBitmap = it
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("修复结果") },
                navigationIcon = {
                    IconButton(onClick = onBackToEditor) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回编辑")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Compare View
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
            ) {
                if (beforeBitmap != null && afterBitmap != null) {
                    CompareView(
                        beforeBitmap = beforeBitmap!!,
                        afterBitmap = afterBitmap!!,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    // Loading state
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }

                // Labels
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Surface(
                        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f),
                        shape = MaterialTheme.shapes.small
                    ) {
                        Text(
                            text = stringResource(R.string.before),
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                            style = MaterialTheme.typography.labelMedium
                        )
                    }
                    Surface(
                        color = Color(0xFF4CAF50).copy(alpha = 0.8f),
                        shape = MaterialTheme.shapes.small
                    ) {
                        Text(
                            text = stringResource(R.string.after),
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                            style = MaterialTheme.typography.labelMedium,
                            color = androidx.compose.ui.graphics.Color.White
                        )
                    }
                }
            }

            // Error message
            errorMessage?.let { error ->
                Snackbar(
                    modifier = Modifier.padding(16.dp),
                    action = {
                        TextButton(onClick = { errorMessage = null }) {
                            Text("关闭")
                        }
                    }
                ) {
                    Text(error)
                }
            }

            // Action buttons
            Surface(
                tonalElevation = 4.dp,
                shadowElevation = 8.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Re-edit button
                    OutlinedButton(
                        onClick = {
                            viewModel.reEdit()
                            onReEdit()
                        },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Edit, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(stringResource(R.string.continue_editing))
                    }

                    // Save button
                    Button(
                        onClick = {
                            scope.launch {
                                isSaving = true
                                try {
                                    saveToGallery(context, afterBitmap!!)
                                    saveSuccess = true
                                    onSaveSuccess()
                                } catch (e: Exception) {
                                    errorMessage = "保存失败: ${e.message}"
                                } finally {
                                    isSaving = false
                                }
                            }
                        },
                        modifier = Modifier.weight(1f),
                        enabled = afterBitmap != null && !isSaving
                    ) {
                        if (isSaving) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.Save, contentDescription = null)
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(stringResource(R.string.save_to_gallery))
                    }
                }
            }
        }
    }

    // Auto-dismiss success message
    LaunchedEffect(saveSuccess) {
        if (saveSuccess) {
            kotlinx.coroutines.delay(2000)
            saveSuccess = false
        }
    }
}

private suspend fun saveToGallery(context: Context, bitmap: Bitmap) {
    withContext(Dispatchers.IO) {
        val filename = "PhotoEraser_${System.currentTimeMillis()}.png"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/PhotoEraser")
            }

            val uri = context.contentResolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                contentValues
            )

            uri?.let {
                context.contentResolver.openOutputStream(it)?.use { outputStream ->
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream)
                }
            }
        } else {
            @Suppress("DEPRECATION")
            val picturesDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
            val photoEraserDir = File(picturesDir, "PhotoEraser")
            if (!photoEraserDir.exists()) {
                photoEraserDir.mkdirs()
            }

            val file = File(photoEraserDir, filename)
            FileOutputStream(file).use { outputStream ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream)
            }

            // Notify gallery
            MediaStore.Images.Media.insertImage(
                context.contentResolver,
                file.absolutePath,
                filename,
                null
            )
        }
    }
}
