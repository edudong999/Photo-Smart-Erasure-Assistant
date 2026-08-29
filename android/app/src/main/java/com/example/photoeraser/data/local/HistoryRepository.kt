package com.example.photoeraser.data.local

import kotlinx.coroutines.flow.Flow
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class HistoryRepository(private val historyDao: HistoryDao) {

    fun getAllHistory(): Flow<List<HistoryEntity>> = historyDao.getAllHistory()

    suspend fun insert(history: HistoryEntity) = historyDao.insert(history)

    suspend fun update(history: HistoryEntity) = historyDao.update(history)

    suspend fun getByTaskId(taskId: String): HistoryEntity? = historyDao.getByTaskId(taskId)

    suspend fun delete(history: HistoryEntity) = historyDao.delete(history)

    suspend fun deleteAll() = historyDao.deleteAll()

    suspend fun updateResult(taskId: String, resultPath: String, status: String) {
        historyDao.updateResult(taskId, resultPath, status)
    }
}

class InpaintRepository(
    private val api: com.example.photoeraser.data.api.PhotoEraserApi,
    private val historyRepository: HistoryRepository
) {
    suspend fun healthCheck(): Result<com.example.photoeraser.data.api.HealthResponse> {
        return try {
            val response = api.healthCheck()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Health check failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitInpaintTask(
        imageFile: File,
        maskFile: File,
        prompt: String? = null
    ): Result<com.example.photoeraser.data.api.InpaintResponse> {
        return try {
            val imageBody = imageFile.asRequestBody("image/*".toMediaTypeOrNull())
            val maskBody = maskFile.asRequestBody("image/*".toMediaTypeOrNull())
            val imagePart = MultipartBody.Part.createFormData("image", imageFile.name, imageBody)
            val maskPart = MultipartBody.Part.createFormData("mask", maskFile.name, maskBody)

            val response = api.submitInpaintTask(imagePart, maskPart, prompt)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Submit failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getTaskStatus(taskId: String): Result<com.example.photoeraser.data.api.TaskStatusResponse> {
        return try {
            val response = api.getTaskStatus(taskId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Get status failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun downloadResult(taskId: String, outputFile: File): Result<File> {
        return try {
            val response = api.downloadResult(taskId)
            if (response.isSuccessful && response.body() != null) {
                saveResponseBodyToFile(response.body()!!, outputFile)
                Result.success(outputFile)
            } else {
                Result.failure(Exception("Download failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun saveResponseBodyToFile(body: ResponseBody, file: File) {
        FileOutputStream(file).use { outputStream ->
            body.byteStream().use { inputStream ->
                inputStream.copyTo(outputStream)
            }
        }
    }
}
