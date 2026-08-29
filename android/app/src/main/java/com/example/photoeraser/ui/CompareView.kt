package com.example.photoeraser.ui

import android.graphics.Bitmap
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import kotlin.math.max
import kotlin.math.min

@Composable
fun CompareView(
    beforeBitmap: Bitmap,
    afterBitmap: Bitmap,
    modifier: Modifier = Modifier
) {
    var splitPosition by remember { mutableStateOf(0.5f) }
    var viewSize by remember { mutableStateOf(IntSize.Zero) }

    Canvas(
        modifier = modifier
            .fillMaxSize()
            .onSizeChanged { viewSize = it }
            .pointerInput(Unit) {
                detectHorizontalDragGestures { change, _ ->
                    change.consume()
                    val newPosition = change.position.x / viewSize.width
                    splitPosition = max(0f, min(1f, newPosition))
                }
            }
    ) {
        if (viewSize.width == 0 || viewSize.height == 0) return@Canvas

        val scaleX = viewSize.width.toFloat() / beforeBitmap.width
        val scaleY = viewSize.height.toFloat() / beforeBitmap.height
        val scale = minOf(scaleX, scaleY)

        val scaledWidth = beforeBitmap.width * scale
        val scaledHeight = beforeBitmap.height * scale
        val offsetX = (viewSize.width - scaledWidth) / 2
        val offsetY = (viewSize.height - scaledHeight) / 2

        val srcRect = Rect(0f, 0f, beforeBitmap.width.toFloat(), beforeBitmap.height.toFloat())
        val dstRect = Rect(offsetX, offsetY, offsetX + scaledWidth, offsetY + scaledHeight)

        val splitX = viewSize.width * splitPosition

        // Draw before (left side)
        clipRect(left = 0f, right = splitX) {
            drawContext.canvas.nativeCanvas.drawBitmap(
                beforeBitmap,
                null,
                android.graphics.Rect(
                    dstRect.left.toInt(),
                    dstRect.top.toInt(),
                    dstRect.right.toInt(),
                    dstRect.bottom.toInt()
                ),
                null
            )
        }

        // Draw after (right side)
        clipRect(left = splitX, right = viewSize.width.toFloat()) {
            drawContext.canvas.nativeCanvas.drawBitmap(
                afterBitmap,
                null,
                android.graphics.Rect(
                    dstRect.left.toInt(),
                    dstRect.top.toInt(),
                    dstRect.right.toInt(),
                    dstRect.bottom.toInt()
                ),
                null
            )
        }

        // Draw split line
        drawLine(
            color = Color.White,
            start = Offset(splitX, 0f),
            end = Offset(splitX, viewSize.height.toFloat()),
            strokeWidth = 4f
        )

        // Draw handle
        val handleRadius = 24f
        drawCircle(
            color = Color.White,
            radius = handleRadius,
            center = Offset(splitX, viewSize.height.toFloat() / 2)
        )
        drawCircle(
            color = Color.Gray,
            radius = handleRadius - 4f,
            center = Offset(splitX, viewSize.height.toFloat() / 2)
        )
    }
}
