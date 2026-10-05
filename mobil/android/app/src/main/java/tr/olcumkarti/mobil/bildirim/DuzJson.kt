package tr.olcumkarti.mobil.bildirim

/** JSON bicim hatasi: mesaj YOK (icerik sir tasiyabilir; hata metnine girmez — tasarim A45, S3). */
class JsonHatasi : Exception("json")

/**
 * Kucuk, KATI JSON okuyucu (RFC 8259). Saf Kotlin: Android'in `org.json`'i JVM birim testinde yok ve
 * gevsek (yorum, tek tirnak, sondaki virgul kabul eder). Bildirim zarflarinin duz metni buradan gecer.
 *  - nesne -> LinkedHashMap<String, Any?> (anahtar sirasi korunur; yinelenen anahtarda SON deger)
 *  - dizi -> List<Any?>; metin -> String; true / false -> Boolean; null -> null
 *  - sayi -> tamsayi ve Long'a sigiyorsa Long, degilse Double
 *  - bastaki BOM, sondaki fazla veri, kacissiz kontrol karakteri, gecersiz kacis: JsonHatasi
 *  - derinlik siniri DERINLIK_AZAMI (kotu niyetli ic ice dizi yigini tasirmasin)
 */
object DuzJson {
    const val DERINLIK_AZAMI = 32

    fun oku(metin: String): Any? {
        val o = Okuyucu(metin)
        o.bosluk()
        val d = o.deger(0)
        o.bosluk()
        if (o.i != metin.length) throw JsonHatasi()
        return d
    }

    /** Kok bir NESNE olmali; degilse JsonHatasi. */
    @Suppress("UNCHECKED_CAST")
    fun nesne(metin: String): Map<String, Any?> = oku(metin) as? Map<String, Any?> ?: throw JsonHatasi()

    private class Okuyucu(private val s: String) {
        var i = 0

        fun bosluk() {
            while (i < s.length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++
        }

        fun deger(derinlik: Int): Any? {
            if (derinlik > DERINLIK_AZAMI || i >= s.length) throw JsonHatasi()
            return when (val c = s[i]) {
                '{' -> nesne(derinlik)
                '[' -> dizi(derinlik)
                '"' -> metin()
                't' -> sabit("true", true)
                'f' -> sabit("false", false)
                'n' -> sabit("null", null)
                else -> if (c == '-' || c in '0'..'9') sayi() else throw JsonHatasi()
            }
        }

        private fun sabit(ad: String, d: Any?): Any? {
            if (!s.startsWith(ad, i)) throw JsonHatasi()
            i += ad.length
            return d
        }

        private fun nesne(derinlik: Int): Map<String, Any?> {
            val m = LinkedHashMap<String, Any?>()
            i++
            bosluk()
            if (i < s.length && s[i] == '}') { i++; return m }
            while (true) {
                bosluk()
                if (i >= s.length || s[i] != '"') throw JsonHatasi()
                val ad = metin()
                bosluk()
                if (i >= s.length || s[i] != ':') throw JsonHatasi()
                i++
                bosluk()
                m[ad] = deger(derinlik + 1)
                bosluk()
                if (i >= s.length) throw JsonHatasi()
                if (s[i] == ',') { i++; continue }
                if (s[i] == '}') { i++; return m }
                throw JsonHatasi()
            }
        }

        private fun dizi(derinlik: Int): List<Any?> {
            val l = ArrayList<Any?>()
            i++
            bosluk()
            if (i < s.length && s[i] == ']') { i++; return l }
            while (true) {
                bosluk()
                l.add(deger(derinlik + 1))
                bosluk()
                if (i >= s.length) throw JsonHatasi()
                if (s[i] == ',') { i++; continue }
                if (s[i] == ']') { i++; return l }
                throw JsonHatasi()
            }
        }

        private fun metin(): String {
            val b = StringBuilder()
            i++
            while (true) {
                if (i >= s.length) throw JsonHatasi()
                val c = s[i++]
                when {
                    c == '"' -> return b.toString()
                    c == '\\' -> {
                        if (i >= s.length) throw JsonHatasi()
                        when (val k = s[i++]) {
                            '"', '\\', '/' -> b.append(k)
                            'b' -> b.append('\b')
                            'f' -> b.append('\u000C')
                            'n' -> b.append('\n')
                            'r' -> b.append('\r')
                            't' -> b.append('\t')
                            'u' -> {
                                if (i + 4 > s.length) throw JsonHatasi()
                                var kod = 0
                                for (j in 0 until 4) {
                                    // Yalniz ASCII onaltilik (Character.digit baska yazilarin rakamlarini da cozer).
                                    val ch = s[i + j]
                                    val h = when (ch) { in '0'..'9' -> ch - '0'; in 'a'..'f' -> ch - 'a' + 10; in 'A'..'F' -> ch - 'A' + 10; else -> throw JsonHatasi() }
                                    kod = kod * 16 + h
                                }
                                i += 4
                                b.append(kod.toChar())
                            }
                            else -> throw JsonHatasi()
                        }
                    }
                    c.code < 0x20 -> throw JsonHatasi()
                    else -> b.append(c)
                }
            }
        }

        private fun sayi(): Any {
            val bas = i
            if (s[i] == '-') i++
            if (i >= s.length) throw JsonHatasi()
            if (s[i] == '0') {
                i++
            } else if (s[i] in '1'..'9') {
                while (i < s.length && s[i] in '0'..'9') i++
            } else {
                throw JsonHatasi()
            }
            var tam = true
            if (i < s.length && s[i] == '.') {
                tam = false
                i++
                if (i >= s.length || s[i] !in '0'..'9') throw JsonHatasi()
                while (i < s.length && s[i] in '0'..'9') i++
            }
            if (i < s.length && (s[i] == 'e' || s[i] == 'E')) {
                tam = false
                i++
                if (i < s.length && (s[i] == '+' || s[i] == '-')) i++
                if (i >= s.length || s[i] !in '0'..'9') throw JsonHatasi()
                while (i < s.length && s[i] in '0'..'9') i++
            }
            val ham = s.substring(bas, i)
            if (tam) ham.toLongOrNull()?.let { return it }
            return ham.toDoubleOrNull() ?: throw JsonHatasi()
        }
    }
}
