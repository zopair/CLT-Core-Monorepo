package com.clt.sovereign.core.network
import com.clt.sovereign.domain.model.AIResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

interface ApiService {
    @POST("webhook/clt-ai")
    suspend fun askAI(@Body request: Map<String, String>): Response<AIResponse>
}