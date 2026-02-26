
package com.clt.sovereign

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.TextView
import android.graphics.Color
import android.view.Gravity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tv = TextView(this)
        tv.text = "CLT SOVEREIGN SYSTEM\nBUILD #34 SUCCESS"
        tv.setTextColor(Color.GREEN)
        tv.textSize = 30f
        tv.gravity = Gravity.CENTER
        setContentView(tv)
    }
}
