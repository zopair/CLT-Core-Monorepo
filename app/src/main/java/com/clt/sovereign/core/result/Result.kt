package com.clt.sovereign.core.result
sealed class Result<out T> {
    data class Success<T>(val data: T): Result<T>()
    data class Failure(val message: String): Result<Nothing>()
}