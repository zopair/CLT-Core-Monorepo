package com.clt.sovereign.ui.viewmodel
import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import com.clt.sovereign.domain.model.AIResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class ChatViewModel @Inject constructor() : ViewModel() {
    var responseState by mutableStateOf("Ready to talk to Gemini...")
    fun sendMessage(msg: String) {
        viewModelScope.launch {
            responseState = "Thinking..."
            // هنا سيتم إضافة ربط الـ UseCase لاحقاً
            responseState = "Gemini says: Received $msg"
        }
    }
}