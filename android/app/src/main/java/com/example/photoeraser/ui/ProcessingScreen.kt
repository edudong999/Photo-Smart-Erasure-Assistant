package com.example.photoeraser.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.photoeraser.R
import com.example.photoeraser.viewmodel.PhotoEraserViewModel
import com.example.photoeraser.viewmodel.ProcessingStatus

@Composable
fun ProcessingScreen(
    viewModel: PhotoEraserViewModel,
    onCancel: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.7f)),
        contentAlignment = Alignment.Center
    ) {
        // Background blur would be applied here in production
        // For now, just show a semi-transparent overlay

        uiState.selectedImagePath?.let { path ->
            AsyncImage(
                model = path,
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
                alpha = 0.3f
            )
        }

        Card(
            modifier = Modifier
                .padding(32.dp)
                .fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.95f)
            )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Animated loading indicator
                LoadingAnimation(
                    status = uiState.processingStatus
                )

                Spacer(modifier = Modifier.height(24.dp))

                // Status text
                Text(
                    text = when (uiState.processingStatus) {
                        ProcessingStatus.Queued -> stringResource(R.string.task_queued)
                        ProcessingStatus.Processing -> stringResource(R.string.ai_fix)
                        ProcessingStatus.Success -> "处理完成"
                        ProcessingStatus.Failed -> "处理失败"
                        else -> stringResource(R.string.processing)
                    },
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Subtitle
                Text(
                    text = when (uiState.processingStatus) {
                        ProcessingStatus.Queued -> "请稍候..."
                        ProcessingStatus.Processing -> "AI 正在修补背景纹理与光影"
                        ProcessingStatus.Success -> "正在准备结果"
                        ProcessingStatus.Failed -> uiState.errorMessage ?: "未知错误"
                        else -> ""
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(32.dp))

                // Cancel button
                if (uiState.processingStatus == ProcessingStatus.Queued ||
                    uiState.processingStatus == ProcessingStatus.Processing) {
                    OutlinedButton(
                        onClick = {
                            viewModel.cancelProcessing()
                            onCancel()
                        }
                    ) {
                        Text(stringResource(R.string.cancel))
                    }
                }
            }
        }
    }
}

@Composable
fun LoadingAnimation(status: ProcessingStatus) {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")

    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    val scale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(750, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    if (status == ProcessingStatus.Success) {
        // Success checkmark animation
        Box(
            modifier = Modifier
                .size(80.dp)
                .background(
                    color = Color(0xFF4CAF50),
                    shape = CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "✓",
                color = Color.White,
                style = MaterialTheme.typography.displayMedium
            )
        }
    } else if (status == ProcessingStatus.Failed) {
        // Failed X animation
        Box(
            modifier = Modifier
                .size(80.dp)
                .background(
                    color = Color(0xFFF44336),
                    shape = CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "✗",
                color = Color.White,
                style = MaterialTheme.typography.displayMedium
            )
        }
    } else {
        // Processing animation
        Box(
            modifier = Modifier
                .size(80.dp)
                .rotate(rotation)
                .scale(scale),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator(
                modifier = Modifier.size(80.dp),
                strokeWidth = 6.dp,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
