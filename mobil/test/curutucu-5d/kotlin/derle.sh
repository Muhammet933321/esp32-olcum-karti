#!/usr/bin/env bash
# Curutucu 5D Kotlin duzenegi: Gradle KOSMAZ, ag yok. Gradle onbellegindeki derleyici jar'i `java` ile calisir.
# Kullanim (mobil/ icinden):   bash test/curutucu-5d/kotlin/derle.sh <cikti-dizini>        (derler + kosar)
# <cikti-dizini>: isletim sisteminin gecici dizininde bos bir klasor (is bitince silinir).
# Cikis kodu = KIRMIZI iddia sayisi (0: kusur duzeltilmis).
set -e
G="$HOME/.gradle/caches/modules-2/files-2.1"
j() { cygpath -w "$(ls $G/$1 | head -1)"; }
STD="$(j 'org.jetbrains.kotlin/kotlin-stdlib/1.9.22/*/kotlin-stdlib-1.9.22.jar')"
CIKTI="$1"
CP="$(j 'org.jetbrains.kotlin/kotlin-compiler-embeddable/1.9.22/*/kotlin-compiler-embeddable-1.9.22.jar');$STD"
CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-script-runtime/1.9.22/*/kotlin-script-runtime-1.9.22.jar')"
CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-reflect/1.6.10/*/kotlin-reflect-1.6.10.jar')"
CP="$CP;$(j 'org.jetbrains.intellij.deps/trove4j/1.0.20200330/*/trove4j-1.0.20200330.jar')"
CP="$CP;$(j 'org.jetbrains/annotations/13.0/*/annotations-13.0.jar')"
CP="$CP;$(j 'org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm/1.6.4/*/kotlinx-coroutines-core-jvm-1.6.4.jar')"
CP="$CP;$(j 'org.jetbrains.kotlin/kotlin-daemon-embeddable/1.9.22/*/kotlin-daemon-embeddable-1.9.22.jar')"
A=android/app/src/main/java/tr/olcumkarti/mobil
java -Xmx512m -cp "$CP" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -nowarn \
  -cp "$STD" -d "$(cygpath -w "$CIKTI")" $A/WebKapi.kt $A/depo/DepoYolu.kt test/curutucu-5d/kotlin/Curutucu5d.kt
java -cp "$(cygpath -w "$CIKTI");$STD" tr.olcumkarti.mobil.Curutucu5dKt
