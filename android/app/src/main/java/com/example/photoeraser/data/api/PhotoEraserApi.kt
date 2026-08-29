package com.example.photoeraser.data.api

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface PhotoEraserApi {

    @GET("/api/v1/health")
    suspend fun healthCheck(): Response<HealthResponse>

    @Multipart
    @POST("/api/v1/inpaint")
    suspend fun submitInpaintTask(
        @Part image: MultipartBody.Part,
        @Part mask: MultipartBody.Part,
        @Part("prompt") prompt: String? = null
    ): Response<InpaintResponse>

    @GET("/api/v1/tasks/{task_id}")
    suspend fun getTaskStatus(
        @Path("task_id") taskId: String
    ): Response<TaskStatusResponse>

    @GET("/api/v1/results/{task_id}.png")
    @Streaming
    suspend fun downloadResult(
        @Path("task_id") taskId: String
    ): Response<ResponseBody>
}
