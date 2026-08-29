package com.example.photoeraser.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface HistoryDao {
    @Query("SELECT * FROM history ORDER BY createdAt DESC")
    fun getAllHistory(): Flow<List<HistoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(history: HistoryEntity)

    @Update
    suspend fun update(history: HistoryEntity)

    @Query("SELECT * FROM history WHERE taskId = :taskId")
    suspend fun getByTaskId(taskId: String): HistoryEntity?

    @Delete
    suspend fun delete(history: HistoryEntity)

    @Query("DELETE FROM history")
    suspend fun deleteAll()

    @Query("UPDATE history SET resultImagePath = :resultPath, status = :status WHERE taskId = :taskId")
    suspend fun updateResult(taskId: String, resultPath: String, status: String)
}
