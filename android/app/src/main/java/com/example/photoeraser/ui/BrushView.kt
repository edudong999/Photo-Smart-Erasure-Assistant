package com.example.photoeraser.ui

import android.graphics.*
import android.view.MotionEvent
import androidx.compose.runtime.*
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import androidx.core.graphics.createBitmap

data class BrushState(
    val paths: MutableList<Pair<Path, Paint>> = mutableListOf(),
    val undonePaths: MutableList<Pair<Path, Paint>> = mutableListOf(),
    val currentPath: Path = Path(),
    val brushSize: Float = 50f,
    val isEraser: Boolean = false
)

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun BrushView(
    originalBitmap: Bitmap,
    brushSize: Float,
    onMaskGenerated: (Bitmap) -> Unit,
    modifier: androidx.compose.ui.Modifier = androidx.compose.ui.Modifier
) {
    var canvasSize by remember { mutableStateOf(IntSize.Zero) }
    var brushState by remember { mutableStateOf(BrushState(brushSize = brushSize)) }
    var maskBitmap by remember { mutableStateOf<Bitmap?>(null) }

    // Update brush size
    LaunchedEffect(brushSize) {
        brushState = brushState.copy(brushSize = brushSize)
    }

    // Initialize mask bitmap when canvas size changes
    LaunchedEffect(canvasSize, originalBitmap) {
        if (canvasSize.width > 0 && canvasSize.height > 0) {
            maskBitmap = createBitmap(canvasSize.width, canvasSize.height).also {
                val canvas = android.graphics.Canvas(it)
                // Draw black background (unmasked area)
                canvas.drawColor(Color.Black.toArgb())
                // Redraw existing paths
                brushState.paths.forEach { (path, paint) ->
                    canvas.drawPath(path, paint)
                }
            }
        }
    }

    androidx.compose.foundation.Canvas(
        modifier = modifier
            .onSizeChanged { size ->
                canvasSize = size
            }
            .pointerInteropFilter { event ->
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        brushState = brushState.copy(
                            currentPath = Path().apply {
                                moveTo(event.x, event.y)
                            }
                        )
                        brushState.undonePaths.clear()
                        true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        brushState.currentPath.lineTo(event.x, event.y)
                        // Draw on mask bitmap
                        maskBitmap?.let { mask ->
                            val canvas = android.graphics.Canvas(mask)
                            val paint = Paint().apply {
                                color = if (brushState.isEraser) Color.Black.toArgb() else Color.White.toArgb()
                                strokeWidth = brushState.brushSize
                                style = Paint.Style.STROKE
                                strokeCap = Paint.Cap.ROUND
                                strokeJoin = Paint.Join.ROUND
                                isAntiAlias = true
                            }
                            canvas.drawPath(brushState.currentPath, paint)
                        }
                        true
                    }
                    MotionEvent.ACTION_UP -> {
                        val paint = Paint().apply {
                            color = if (brushState.isEraser) Color.Black.toArgb() else Color.White.toArgb()
                            strokeWidth = brushState.brushSize
                            style = Paint.Style.STROKE
                            strokeCap = Paint.Cap.ROUND
                            strokeJoin = Paint.Join.ROUND
                            isAntiAlias = true
                        }
                        brushState = brushState.copy(
                            paths = (brushState.paths + Pair(brushState.currentPath, paint)).toMutableList(),
                            currentPath = Path()
                        )
                        onMaskGenerated(maskBitmap!!)
                        true
                    }
                    else -> false
                }
            }
    ) {
        // Draw original bitmap scaled to fit
        val scaleX = size.width / originalBitmap.width
        val scaleY = size.height / originalBitmap.height
        val scale = minOf(scaleX, scaleY)

        val scaledWidth = originalBitmap.width * scale
        val scaledHeight = originalBitmap.height * scale
        val offsetX = (size.width - scaledWidth) / 2
        val offsetY = (size.height - scaledHeight) / 2

        drawContext.canvas.nativeCanvas.apply {
            save()
            translate(offsetX, offsetY)
            scale(scale, scale)
            drawBitmap(originalBitmap, 0f, 0f, null)
            restore()
        }

        // Draw mask overlay (green tint for painted areas)
        maskBitmap?.let { mask ->
            val maskPaint = Paint().apply {
                alpha = 80
            }
            drawContext.canvas.nativeCanvas.apply {
                save()
                translate(offsetX, offsetY)
                scale(scale, scale)
                drawBitmap(mask, 0f, 0f, maskPaint)
                restore()
            }
        }

        // Draw current stroke preview
        if (brushState.currentPath.isEmpty.not()) {
            val previewPaint = Paint().apply {
                color = if (brushState.isEraser) Color.Black.copy(alpha = 0.5f).toArgb()
                else Color.Green.copy(alpha = 0.5f).toArgb()
                strokeWidth = brushState.brushSize
                style = Paint.Style.STROKE
                strokeCap = Paint.Cap.ROUND
                strokeJoin = Paint.Join.ROUND
                isAntiAlias = true
            }
            drawContext.canvas.nativeCanvas.apply {
                save()
                translate(offsetX, offsetY)
                scale(scale, scale)
                drawPath(brushState.currentPath, previewPaint)
                restore()
            }
        }
    }
}

fun generateMaskBitmap(canvasSize: IntSize, paths: List<Pair<Path, Paint>>): Bitmap {
    return createBitmap(canvasSize.width, canvasSize.height).also { bitmap ->
        val canvas = android.graphics.Canvas(bitmap)
        // Black background
        canvas.drawColor(Color.Black.toArgb())
        // Draw all paths in white
        paths.forEach { (path, paint) ->
            paint.color = Color.White.toArgb()
            canvas.drawPath(path, paint)
        }
    }
}
