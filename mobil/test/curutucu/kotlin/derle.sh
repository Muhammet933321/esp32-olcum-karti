#!/usr/bin/env bash
# Curutucu Kotlin duzenegi: Gradle KOSMAZ. Gradle'in yerel onbellegindeki kotlin derleyici jar'ini
# dogrudan `java` ile calistirir (ag yok). Kullanim (mobil/ icinden):
#   bash test/curutucu/kotlin/derle.sh <cikti-dizini>          # derler
#   bash test/curutucu/kotlin/derle.sh <cikti-dizini> http     # derlenmisi kosar (HttpIstek kanitlari)
#   bash test/curutucu/kotlin/derle.sh <cikti-dizini> fark <girdi> <cikti>
set -e
G="$HOME/.gradle/caches/modules-2/files-2.1"
j() { cygpath -w "$(ls $G/$1 | head -1)"; }
STD="$(j 'org.jetbrains.kotlin/kotlin-stdlib/1.9.22/*/kotlin-stdlib-1.9.22.jar')"
CIKTI="$1"; shift
if [ $# -eq 0 ]; then
  CP="$(j 'org.jetbrains.kotlin/kotlin-compiler-embeddable/1.9.22/*/kotlin-compiler-embeddable-1.9.22.jar');$STD"
  CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-script-runtime/1.9.22/*/kotlin-script-runtime-1.9.22.jar')"
  CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-reflect/1.6.10/*/kotlin-reflect-1.6.10.jar')"
  CP="$CP;$(j 'org.jetbrains.intellij.deps/trove4j/1.0.20200330/*/trove4j-1.0.20200330.jar')"
  CP="$CP;$(j 'org.jetbrains/annotations/13.0/*/annotations-13.0.jar')"
  CP="$CP;$(j 'org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm/1.6.4/*/kotlinx-coroutines-core-jvm-1.6.4.jar')"
  CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-daemon-embeddable/1.9.22/*/kotlin-daemon-embeddable-1.9.22.jar')"
  A=android/app/src/main/java/tr/olcumkarti/mobil/ag
  java -Xmx512m -cp "$CP" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -nowarn \
    -cp "$STD" -d "$(cygpath -w "$CIKTI")" $A/Hedef.kt $A/HttpIstek.kt test/curutucu/kotlin/Curutucu.kt
else
  java -cp "$(cygpath -w "$CIKTI");$STD" tr.olcumkarti.mobil.ag.CurutucuKt "$@"
fi
