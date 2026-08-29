package com.example.photoeraser.data.api

import com.google.gson.annotations.SerializedName

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("ai_reachable") val aiReachable: Boolean,
    @SerializedName("version") val version: String?
)

data class InpaintResponse(
    @SerializedName("task_id") val taskId: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("expires_at") val expiresAt: String?
)

data class TaskStatusResponse(
    @SerializedName("task_id") val taskId: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("result") val result: TaskResult?,
    @SerializedName("error") val error: TaskError?
)

data class TaskResult(
    @SerializedName("result_url") val resultUrl: String,
    @SerializedName("expires_at") val expiresAt: String,
    @SerializedName("width") val width: Int,
    @SerializedName("height") val height: Int,
    @SerializedName("bytes") val bytes: Int
)

data class TaskError(
    @SerializedName("code") val code: String,
    @SerializedName("message") val message: String
)
