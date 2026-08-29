package com.example.photoeraser.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "history")
data class HistoryEntity(
    @PrimaryKey
    val taskId: String,
    val originalImagePath: String,
    val resultImagePath: String?,
    val taskId_: String,
    val createdAt: Long,
    val status: String,
    val thumbnailPath: String?
)
