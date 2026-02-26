
package com.clt.sovereign.domain.models
import java.util.Date
data class ChatMessage(val prompt: String, val answer: String?, val timestamp: Date)