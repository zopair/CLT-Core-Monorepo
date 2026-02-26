#!/bin/sh
# CLT Sovereign Wrapper Trigger
gradle wrapper --gradle-version 8.2
exec ./gradlew "$@"
