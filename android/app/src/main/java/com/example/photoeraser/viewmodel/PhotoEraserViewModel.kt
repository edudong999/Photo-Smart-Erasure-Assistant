package com.example.photoeraser.viewmodel

import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.photoeraser.data.local.HistoryEntity
import com.example.photoeraser.data.local.HistoryRepository
import com.example.photoeraser.data.local.InpaintRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

data class UiState(
    val aiStatus: AiStatus = AiStatus.Checking,
    val currentScreen: Screen = Screen.Home,
    val selectedImageUri: Uri? = null,
    val selectedImagePath: String? = null,
    val originalBitmap: Bitmap? = null,
    val maskBitmap: Bitmap? = null,
    val resultBitmap: Bitmap? = null,
    val taskId: String? = null,
    val processingStatus: ProcessingStatus = ProcessingStatus.Idle,
    val errorMessage: String? = null,
    val brushSize: Float = 50f,
    val historyList: List<HistoryEntity> = emptyList()
)

enum class AiStatus {
    Checking, Ready, NotReachable
}

enum class Screen {
    Home, Editor, Processing, Result
}

enum class ProcessingStatus {
    Idle, Queued, Processing, Success, Failed
}

class PhotoEraserViewModel(
    private val historyRepository: HistoryRepository,
    private val inpaintRepository: InpaintRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private var pollingJob: Job? = null

    init {
        loadHistory()
        checkHealth()
    }

    private fun loadHistory() {
        viewModelScope.launch {
            historyRepository.getAllHistory().collect { history ->
                _uiState.value = _uiState.value.copy(historyList = history)
            }
        }
    }

    fun checkHealth() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(aiStatus = AiStatus.Checking)
            val result = inpaintRepository.healthCheck()
            _uiState.value = _uiState.value.copy(
                aiStatus = if (result.isSuccess && result.getOrNull()?.aiReachable == true) {
                    AiStatus.Ready
                } else {
                    AiStatus.NotReachable
                }
            )
        }
    }

    fun selectImage(uri: Uri, imagePath: String) {
        _uiState.value = _uiState.value.copy(
            selectedImageUri = uri,
            selectedImagePath = imagePath,
            currentScreen = Screen.Editor,
            resultBitmap = null,
            maskBitmap = null
        )
    }

    fun setOriginalBitmap(bitmap: Bitmap) {
        _uiState.value = _uiState.value.copy(originalBitmap = bitmap)
    }

    fun setMaskBitmap(bitmap: Bitmap) {
        _uiState.value = _uiState.value.copy(maskBitmap = bitmap)
    }

    fun setBrushSize(size: Float) {
        _uiState.value = _uiState.value.copy(brushSize = size)
    }

    fun navigateTo(screen: Screen) {
        _uiState.value = _uiState.value.copy(currentScreen = screen)
    }

    fun submitInpaintTask(imageFile: File, maskFile: File) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                currentScreen = Screen.Processing,
                processingStatus = ProcessingStatus.Queued
            )

            val result = inpaintRepository.submitInpaintTask(imageFile, maskFile)
            if (result.isSuccess) {
                val taskId = result.getOrNull()!!.taskId
                _uiState.value = _uiState.value.copy(
                    taskId = taskId,
                    processingStatus = ProcessingStatus.Processing
                )
                // Save to history
                historyRepository.insert(
                    HistoryEntity(
                        taskId = taskId,
                        originalImagePath = imageFile.absolutePath,
                        resultImagePath = null,
                        taskId_ = taskId,
                        createdAt = System.currentTimeMillis(),
                        status = "processing",
                        thumbnailPath = null
                    )
                )
                // Start polling
                startPolling(taskId)
            } else {
                _uiState.value = _uiState.value.copy(
                    processingStatus = ProcessingStatus.Failed,
                    errorMessage = result.exceptionOrNull()?.message ?: "提交失败"
                )
            }
        }
    }

    private fun startPolling(taskId: String) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                delay(1500) // Poll every 1.5 seconds
                val statusResult = inpaintRepository.getTaskStatus(taskId)
                if (statusResult.isSuccess) {
                    val status = statusResult.getOrNull()!!
                    when (status.status) {
                        "success" -> {
                            _uiState.value = _uiState.value.copy(
                                processingStatus = ProcessingStatus.Success
                            )
                            // Update history
                            historyRepository.updateResult(taskId, "", "success")
                            // Navigate to result screen
                            _uiState.value = _uiState.value.copy(currentScreen = Screen.Result)
                            break
                        }
                        "failed" -> {
                            _uiState.value = _uiState.value.copy(
                                processingStatus = ProcessingStatus.Failed,
                                errorMessage = status.error?.message ?: "处理失败"
                            )
                            historyRepository.updateResult(taskId, "", "failed")
                            break
                        }
                        "submitted", "processing" -> {
                            _uiState.value = _uiState.value.copy(
                                processingStatus = ProcessingStatus.Processing
                            )
                        }
                    }
                } else {
                    // Network error, continue polling
                }
            }
        }
    }

    fun downloadAndLoadResult(context: android.content.Context, taskId: String) {
        viewModelScope.launch {
            val tempFile = java.io.File(context.cacheDir, "result_${taskId}.png")
            val result = inpaintRepository.downloadResult(taskId, tempFile)
            if (result.isSuccess) {
                val bitmap = android.graphics.BitmapFactory.decodeFile(tempFile.absolutePath)
                _uiState.value = _uiState.value.copy(resultBitmap = bitmap)
                // Update history with result path
                historyRepository.updateResult(taskId, tempFile.absolutePath, "success")
            }
        }
    }

    fun cancelProcessing() {
        pollingJob?.cancel()
        _uiState.value = _uiState.value.copy(
            currentScreen = Screen.Editor,
            processingStatus = ProcessingStatus.Idle
        )
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(errorMessage = null)
    }

    fun clearHistory() {
        viewModelScope.launch {
            historyRepository.deleteAll()
        }
    }

    fun reEdit() {
        _uiState.value = _uiState.value.copy(
            currentScreen = Screen.Editor,
            resultBitmap = null,
            processingStatus = ProcessingStatus.Idle
        )
    }

    override fun onCleared() {
        super.onCleared()
        pollingJob?.cancel()
    }
}

class PhotoEraserViewModelFactory(
    private val historyRepository: HistoryRepository,
    private val inpaintRepository: InpaintRepository
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(PhotoEraserViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return PhotoEraserViewModel(historyRepository, inpaintRepository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
