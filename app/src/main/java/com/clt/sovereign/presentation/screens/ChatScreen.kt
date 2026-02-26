
package com.clt.sovereign.presentation.screens
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ChatScreen(lastResponse: String = "Ready") {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(text = "CLT SOVEREIGN AI", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(20.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Text(padding(16.dp), text = lastResponse)
        }
    }
}