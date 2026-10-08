package com.example.android_app

import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    // Android emulator에서 호스트 PC의 Django 서버에 접속하는 주소
    private val baseUrl = "http://10.0.2.2:8000/"
    private lateinit var selectedImage: Uri
    private lateinit var imageView: ImageView
    private lateinit var statusText: TextView
    private lateinit var postsContainer: LinearLayout
    private lateinit var authorIdInput: EditText
    private lateinit var titleInput: EditText
    private lateinit var textInput: EditText

    private val api by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(PhotoBlogApi::class.java)
    }

    private val imagePicker = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let {
            selectedImage = it
            imageView.setImageURI(it)
            statusText.text = "이미지가 선택되었습니다."
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        imageView = findViewById(R.id.imageView)
        statusText = findViewById(R.id.statusText)
        postsContainer = findViewById(R.id.postsContainer)
        authorIdInput = findViewById(R.id.authorIdInput)
        titleInput = findViewById(R.id.titleInput)
        textInput = findViewById(R.id.textInput)

        findViewById<Button>(R.id.selectImageButton).setOnClickListener {
            imagePicker.launch("image/*")
        }
        findViewById<Button>(R.id.uploadButton).setOnClickListener { uploadPost() }
        loadPosts()
    }

    private fun uploadPost() {
        if (!::selectedImage.isInitialized) {
            statusText.text = "먼저 이미지를 선택하세요."
            return
        }

        val bytes = contentResolver.openInputStream(selectedImage)?.use { it.readBytes() }
        if (bytes == null) {
            statusText.text = "이미지를 읽을 수 없습니다."
            return
        }

        val fileName = queryFileName(selectedImage) ?: "photo.jpg"
        val mediaType = contentResolver.getType(selectedImage)?.toMediaTypeOrNull()
            ?: "image/*".toMediaTypeOrNull()
        val imagePart = MultipartBody.Part.createFormData(
            "image", fileName, bytes.toRequestBody(mediaType)
        )

        statusText.text = "업로드 중..."
        api.createPost(
            authorIdInput.text.toString().toRequestBody("text/plain".toMediaTypeOrNull()),
            titleInput.text.toString().toRequestBody("text/plain".toMediaTypeOrNull()),
            textInput.text.toString().toRequestBody("text/plain".toMediaTypeOrNull()),
            imagePart
        ).enqueue(object : Callback<Post> {
            override fun onResponse(call: Call<Post>, response: Response<Post>) {
                if (response.isSuccessful) {
                    statusText.text = "업로드 완료 · 동기화 중..."
                    loadPosts()
                } else {
                    statusText.text = "업로드 실패: HTTP ${response.code()}"
                }
            }

            override fun onFailure(call: Call<Post>, t: Throwable) {
                statusText.text = "네트워크 오류: ${t.message}"
            }
        })
    }

    private fun loadPosts() {
        api.getPosts().enqueue(object : Callback<List<Post>> {
            override fun onResponse(call: Call<List<Post>>, response: Response<List<Post>>) {
                if (!response.isSuccessful) {
                    statusText.text = "게시글 조회 실패: HTTP ${response.code()}"
                    return
                }
                postsContainer.removeAllViews()
                response.body().orEmpty().forEach { addPostView(it) }
                statusText.text = "동기화 완료 · ${response.body().orEmpty().size}개 게시글"
            }

            override fun onFailure(call: Call<List<Post>>, t: Throwable) {
                statusText.text = "서버 연결 실패: ${t.message}"
            }
        })
    }

    private fun addPostView(post: Post) {
        val title = TextView(this).apply {
            text = "${post.title}\n${post.text}"
            textSize = 18f
            setPadding(0, 20, 0, 8)
        }
        postsContainer.addView(title)

        post.image?.let { imagePath ->
            val image = ImageView(this).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, 240
                )
                scaleType = ImageView.ScaleType.CENTER_CROP
            }
            postsContainer.addView(image)
            Executors.newSingleThreadExecutor().execute {
                try {
                    val url = imagePath
                        .replace("http://127.0.0.1:8000", baseUrl.trimEnd('/'))
                        .replace("http://localhost:8000", baseUrl.trimEnd('/'))
                        .let { if (it.startsWith("http")) it else baseUrl.trimEnd('/') + it }
                    val connection = URL(url).openConnection() as HttpURLConnection
                    val bitmap = connection.inputStream.use { BitmapFactory.decodeStream(it) }
                    runOnUiThread { image.setImageBitmap(bitmap) }
                } catch (_: Exception) {
                    // 텍스트 목록은 이미지 로딩 실패와 관계없이 표시한다.
                }
            }
        }
    }

    private fun queryFileName(uri: Uri): String? {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { cursor ->
                if (cursor.moveToFirst()) return cursor.getString(0)
            }
        return null
    }
}

data class Post(
    val id: Int,
    val author: Int,
    val title: String,
    val text: String,
    val image: String?
)

interface PhotoBlogApi {
    @GET("api_root/Post/")
    fun getPosts(): Call<List<Post>>

    @Multipart
    @POST("api_root/Post/")
    fun createPost(
        @Part("author") author: RequestBody,
        @Part("title") title: RequestBody,
        @Part("text") text: RequestBody,
        @Part image: MultipartBody.Part
    ): Call<Post>
}
