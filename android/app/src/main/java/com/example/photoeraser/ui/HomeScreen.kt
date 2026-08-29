package com.example.photoeraser.ui

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.photoeraser.R
import com.example.photoeraser.data.local.HistoryEntity
import com.example.photoeraser.viewmodel.AiStatus
import com.example.photoeraser.viewmodel.PhotoEraserViewModel
import java.io.File
import java.io.FileOutputStream

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    viewModel: PhotoEraserViewModel,
    onImageSelected: (Uri, String) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var tempImagePath by remember { mutableStateOf<String?>(null) }

    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            val path = copyUriToTempFile(context, it)
            if (path != null) {
                tempImagePath = path
                onImageSelected(it, path)
            }
        }
    }

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            tempImagePath?.let { path ->
                val uri = Uri.fromFile(File(path))
                onImageSelected(uri, path)
            }
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            val tempFile = createTempImageFile(context)
            tempImagePath = tempFile.absolutePath
            cameraLauncher.launch(Uri.fromFile(tempFile))
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.app_name)) },
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
                .padding(16.dp)
        ) {
            // AI Status Card
            AiStatusCard(
                aiStatus = uiState.aiStatus,
                onRetry = { viewModel.checkHealth() }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                ActionCard(
                    icon = Icons.Default.PhotoLibrary,
                    title = stringResource(R.string.select_from_album),
                    modifier = Modifier.weight(1f),
                    onClick = { imagePickerLauncher.launch("image/*") }
                )

                ActionCard(
                    icon = Icons.Default.CameraAlt,
                    title = stringResource(R.string.take_photo),
                    modifier = Modifier.weight(1f),
                    onClick = { cameraPermissionLauncher.launch(Manifest.permission.CAMERA) }
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // History Section
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = stringResource(R.string.history),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                if (uiState.historyList.isNotEmpty()) {
                    TextButton(onClick = { viewModel.clearHistory() }) {
                        Text(stringResource(R.string.clear_history))
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (uiState.historyList.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = stringResource(R.string.no_history),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(uiState.historyList) { history ->
                        HistoryCard(
                            history = history,
                            onClick = {
                                // Load history item for re-editing
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun AiStatusCard(
    aiStatus: AiStatus,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (aiStatus) {
                AiStatus.Ready -> Color(0xFF4CAF50).copy(alpha = 0.1f)
                AiStatus.NotReachable -> Color(0xFFF44336).copy(alpha = 0.1f)
                AiStatus.Checking -> Color(0xFFFF9800).copy(alpha = 0.1f)
            }
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = when (aiStatus) {
                        AiStatus.Ready -> Icons.Default.CheckCircle
                        AiStatus.NotReachable -> Icons.Default.Error
                        AiStatus.Checking -> Icons.Default.HourglassEmpty
                    },
                    contentDescription = null,
                    tint = when (aiStatus) {
                        AiStatus.Ready -> Color(0xFF4CAF50)
                        AiStatus.NotReachable -> Color(0xFFF44336)
                        AiStatus.Checking -> Color(0xFFFF9800)
                    }
                )
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    text = when (aiStatus) {
                        AiStatus.Ready -> stringResource(R.string.ai_status_ready)
                        AiStatus.NotReachable -> stringResource(R.string.ai_status_not_reachable)
                        AiStatus.Checking -> stringResource(R.string.ai_status_checking)
                    },
                    fontWeight = FontWeight.Medium
                )
            }
            if (aiStatus == AiStatus.NotReachable) {
                TextButton(onClick = onRetry) {
                    Text("重试")
                }
            }
        }
    }
}

@Composable
fun ActionCard(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier
            .aspectRatio(1f)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = title,
                modifier = Modifier.size(48.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
fun HistoryCard(
    history: HistoryEntity,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(0.75f)
            .clickable(onClick = onClick)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Show thumbnail if available
            history.thumbnailPath?.let { path ->
                val bitmap = remember { BitmapFactory.decodeFile(path) }
                bitmap?.let {
                    Image(
                        bitmap = it.asImageBitmap(),
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )
                }
            }

            // Status indicator
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(8.dp)
                    .background(
                        color = when (history.status) {
                            "success" -> Color(0xFF4CAF50)
                            "failed" -> Color(0xFFF44336)
                            else -> Color(0xFFFF9800)
                        },
                        shape = RoundedCornerShape(4.dp)
                    )
                    .padding(horizontal = 6.dp, vertical = 2.dp)
            ) {
                Text(
                    text = when (history.status) {
                        "success" -> "完成"
                        "failed" -> "失败"
                        else -> "处理中"
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White
                )
            }
        }
    }
}

private fun copyUriToTempFile(context: Context, uri: Uri): String? {
    return try {
        val inputStream = context.contentResolver.openInputStream(uri) ?: return null
        val tempFile = File(context.cacheDir, "temp_${System.currentTimeMillis()}.jpg")
        FileOutputStream(tempFile).use { output ->
            inputStream.copyTo(output)
        }
        inputStream.close()
        tempFile.absolutePath
    } catch (e: Exception) {
        null
    }
}

private fun createTempImageFile(context: Context): File {
    return File(context.cacheDir, "camera_${System.currentTimeMillis()}.jpg")
}
