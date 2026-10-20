#!/usr/bin/env python3
"""Interactive Flutter starter generator. Python 3.9+, no pip dependencies.
Run: python flutter_project_creator.py
Help: python flutter_project_creator.py --help
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

MANAGERS = ('provider', 'riverpod', 'bloc', 'cubit', 'getx', 'setstate')
PACKAGES = {'provider': ['provider:^6.1.0'], 'riverpod': ['flutter_riverpod:^3.0.0'],
            'bloc': ['flutter_bloc:^9.0.0'], 'cubit': ['flutter_bloc:^9.0.0'],
            'getx': ['get:^4.6.6'], 'setstate': []}
PLATFORMS = {'android', 'ios', 'web', 'windows', 'macos', 'linux'}
RESERVED = set('abstract as assert async await break case catch class const continue covariant default deferred do dynamic else enum export extends extension external factory false final finally for Function get hide if implements import in interface is late library mixin new null of on operator part required rethrow return sealed set show static super switch sync this throw true try typedef var void when while with yield'.lower().split())

# Original files from the supplied api_manager.zip. No network download required.
API_MANAGER_FILES = {'lib/api/api.dart': '/// Import this single file to use the API layer.\n'
                     'library;\n'
                     '\n'
                     "export 'api_client.dart';\n"
                     "export 'api_config.dart';\n"
                     "export 'api_exception.dart';\n"
                     "export 'api_file.dart';\n"
                     "export 'api_logger.dart';\n"
                     "export 'api_manager.dart';\n"
                     "export 'dio_api_client.dart';\n"
                     "export 'http_api_client.dart';\n",
 'lib/api/api_client.dart': "import 'dart:convert';\n"
                            '\n'
                            "import 'package:flutter/foundation.dart';\n"
                            '\n'
                            "import 'api_config.dart';\n"
                            "import 'api_exception.dart';\n"
                            "import 'api_file.dart';\n"
                            "import 'api_logger.dart';\n"
                            '\n'
                            'enum HttpMethod {\n'
                            '  get,\n'
                            '  post,\n'
                            '  put,\n'
                            '  patch,\n'
                            '  delete;\n'
                            '\n'
                            '  String get value => name.toUpperCase();\n'
                            '}\n'
                            '\n'
                            '/// How the response body should be returned.\n'
                            'enum ApiResponseType {\n'
                            '  /// Decoded JSON (Map / List). Falls back to a String if the body is not '
                            'JSON.\n'
                            '  json,\n'
                            '\n'
                            '  /// The body as a String.\n'
                            '  text,\n'
                            '\n'
                            '  /// The raw bytes as a [Uint8List] (images, PDFs, any binary file).\n'
                            '  bytes,\n'
                            '}\n'
                            '\n'
                            '/// Called with bytes transferred so far and the total (-1 if unknown).\n'
                            'typedef ApiProgressCallback = void Function(int count, int total);\n'
                            '\n'
                            '/// Converts the response body into your model.\n'
                            'typedef JsonParser<T> = T Function(dynamic json);\n'
                            '\n'
                            '/// Everything a transport needs to perform one request.\n'
                            'class ApiRequest {\n'
                            '  const ApiRequest({\n'
                            '    required this.method,\n'
                            '    required this.uri,\n'
                            '    required this.headers,\n'
                            '    this.body,\n'
                            '    this.responseType = ApiResponseType.json,\n'
                            '    this.savePath,\n'
                            '    this.onSendProgress,\n'
                            '    this.onReceiveProgress,\n'
                            '  });\n'
                            '\n'
                            '  final HttpMethod method;\n'
                            '  final Uri uri;\n'
                            '  final Map<String, String> headers;\n'
                            '\n'
                            '  /// null, String, `List<int>`, [ApiFile], [ApiFormData], or anything\n'
                            '  /// JSON-encodable (Map, List, ...).\n'
                            '  final Object? body;\n'
                            '  final ApiResponseType responseType;\n'
                            '\n'
                            '  /// When set, a 2xx response body is streamed to this file instead of\n'
                            '  /// being returned.\n'
                            '  final String? savePath;\n'
                            '  final ApiProgressCallback? onSendProgress;\n'
                            '  final ApiProgressCallback? onReceiveProgress;\n'
                            '}\n'
                            '\n'
                            '/// Transport-level response returned by [ApiClient.send].\n'
                            'class ApiResponse {\n'
                            '  const ApiResponse({\n'
                            '    required this.statusCode,\n'
                            '    this.data,\n'
                            '    this.headers = const {},\n'
                            '  });\n'
                            '\n'
                            '  final int statusCode;\n'
                            '\n'
                            '  /// Decoded according to [ApiRequest.responseType], or the save path\n'
                            '  /// for downloads.\n'
                            '  final dynamic data;\n'
                            '  final Map<String, String> headers;\n'
                            '\n'
                            '  bool get isSuccess => statusCode >= 200 && statusCode < 300;\n'
                            '}\n'
                            '\n'
                            '/// Common interface for every HTTP backend.\n'
                            '///\n'
                            '/// URL building, headers, auth, logging, status checks and parsing live here.\n'
                            '/// Subclasses implement only [send] (the actual network call) and [close].\n'
                            'abstract class ApiClient {\n'
                            '  ApiClient(ApiConfig config)\n'
                            '      : _config = config,\n'
                            '        _authToken = config.authToken,\n'
                            '        _logger = _createLogger(config);\n'
                            '\n'
                            '  ApiConfig _config;\n'
                            '  String? _authToken;\n'
                            '  ApiLogger _logger;\n'
                            '\n'
                            '  ApiConfig get config => _config;\n'
                            '  String? get authToken => _authToken;\n'
                            '\n'
                            '  /// Set after login, or pass `null` on logout.\n'
                            '  void setAuthToken(String? token) => _authToken = token;\n'
                            '\n'
                            '  /// Replace the config at runtime (e.g. switch base URL or environment).\n'
                            '  void updateConfig(ApiConfig config) {\n'
                            '    _config = config;\n'
                            '    _logger = _createLogger(config);\n'
                            '    onConfigChanged();\n'
                            '  }\n'
                            '\n'
                            '  // ---------- Public API ----------\n'
                            '\n'
                            '  Future<T> get<T>(\n'
                            '    String path, {\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) =>\n'
                            '      request<T>(HttpMethod.get, path,\n'
                            '          query: query,\n'
                            '          headers: headers,\n'
                            '          parser: parser,\n'
                            '          responseType: responseType,\n'
                            '          onReceiveProgress: onReceiveProgress);\n'
                            '\n'
                            '  Future<T> post<T>(\n'
                            '    String path, {\n'
                            '    Object? body,\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '    ApiProgressCallback? onSendProgress,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) =>\n'
                            '      request<T>(HttpMethod.post, path,\n'
                            '          body: body,\n'
                            '          query: query,\n'
                            '          headers: headers,\n'
                            '          parser: parser,\n'
                            '          responseType: responseType,\n'
                            '          onSendProgress: onSendProgress,\n'
                            '          onReceiveProgress: onReceiveProgress);\n'
                            '\n'
                            '  Future<T> put<T>(\n'
                            '    String path, {\n'
                            '    Object? body,\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '    ApiProgressCallback? onSendProgress,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) =>\n'
                            '      request<T>(HttpMethod.put, path,\n'
                            '          body: body,\n'
                            '          query: query,\n'
                            '          headers: headers,\n'
                            '          parser: parser,\n'
                            '          responseType: responseType,\n'
                            '          onSendProgress: onSendProgress,\n'
                            '          onReceiveProgress: onReceiveProgress);\n'
                            '\n'
                            '  Future<T> patch<T>(\n'
                            '    String path, {\n'
                            '    Object? body,\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '    ApiProgressCallback? onSendProgress,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) =>\n'
                            '      request<T>(HttpMethod.patch, path,\n'
                            '          body: body,\n'
                            '          query: query,\n'
                            '          headers: headers,\n'
                            '          parser: parser,\n'
                            '          responseType: responseType,\n'
                            '          onSendProgress: onSendProgress,\n'
                            '          onReceiveProgress: onReceiveProgress);\n'
                            '\n'
                            '  Future<T> delete<T>(\n'
                            '    String path, {\n'
                            '    Object? body,\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '  }) =>\n'
                            '      request<T>(HttpMethod.delete, path,\n'
                            '          body: body,\n'
                            '          query: query,\n'
                            '          headers: headers,\n'
                            '          parser: parser,\n'
                            '          responseType: responseType);\n'
                            '\n'
                            '  /// Downloads [path] and streams it into the file at [savePath].\n'
                            '  /// Returns [savePath]. Not supported on Flutter Web: use\n'
                            '  /// `get(path, responseType: ApiResponseType.bytes)` there instead.\n'
                            '  Future<String> download(\n'
                            '    String path,\n'
                            '    String savePath, {\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) {\n'
                            '    return _execute<String>(\n'
                            '      ApiRequest(\n'
                            '        method: HttpMethod.get,\n'
                            '        uri: buildUri(path, query),\n'
                            '        headers: buildHeaders(headers),\n'
                            '        responseType: ApiResponseType.bytes,\n'
                            '        savePath: savePath,\n'
                            '        onReceiveProgress: onReceiveProgress,\n'
                            '      ),\n'
                            '      null,\n'
                            '    );\n'
                            '  }\n'
                            '\n'
                            '  /// Sends a request and returns the parsed result.\n'
                            '  /// Throws [ApiException] on any failure.\n'
                            '  Future<T> request<T>(\n'
                            '    HttpMethod method,\n'
                            '    String path, {\n'
                            '    Object? body,\n'
                            '    Map<String, dynamic>? query,\n'
                            '    Map<String, String>? headers,\n'
                            '    JsonParser<T>? parser,\n'
                            '    ApiResponseType responseType = ApiResponseType.json,\n'
                            '    ApiProgressCallback? onSendProgress,\n'
                            '    ApiProgressCallback? onReceiveProgress,\n'
                            '  }) {\n'
                            '    return _execute<T>(\n'
                            '      ApiRequest(\n'
                            '        method: method,\n'
                            '        uri: buildUri(path, query),\n'
                            '        headers: buildHeaders(headers, body: body),\n'
                            '        body: body,\n'
                            '        responseType: responseType,\n'
                            '        onSendProgress: onSendProgress,\n'
                            '        onReceiveProgress: onReceiveProgress,\n'
                            '      ),\n'
                            '      parser,\n'
                            '    );\n'
                            '  }\n'
                            '\n'
                            '  /// Releases the underlying connection pool.\n'
                            '  void close();\n'
                            '\n'
                            '  // ---------- For subclasses ----------\n'
                            '\n'
                            '  /// Performs the network call. Return the response for any status code;\n'
                            '  /// throw [ApiException] for transport failures (network, timeout, cancel).\n'
                            '  @protected\n'
                            '  Future<ApiResponse> send(ApiRequest request);\n'
                            '\n'
                            '  /// Called after [updateConfig].\n'
                            '  @protected\n'
                            '  void onConfigChanged() {}\n'
                            '\n'
                            '  /// Joins [path] onto the base URL. Absolute URLs are used as given.\n'
                            '  @protected\n'
                            '  Uri buildUri(String path, Map<String, dynamic>? query) {\n'
                            '    final isAbsolute =\n'
                            "        path.startsWith('http://') || path.startsWith('https://');\n"
                            "    final base = _config.baseUrl.endsWith('/')\n"
                            '        ? _config.baseUrl.substring(0, _config.baseUrl.length - 1)\n'
                            '        : _config.baseUrl;\n'
                            "    final relative = path.startsWith('/') ? path.substring(1) : path;\n"
                            '    final uri = Uri.parse(\n'
                            "        isAbsolute ? path : (relative.isEmpty ? base : '$base/$relative'));\n"
                            '\n'
                            '    if (query == null || query.isEmpty) return uri;\n'
                            '    return uri.replace(queryParameters: {\n'
                            '      ...uri.queryParametersAll,\n'
                            '      for (final e in query.entries)\n'
                            '        if (e.value != null)\n'
                            '          e.key: e.value is Iterable\n'
                            "              ? (e.value as Iterable).map((v) => '$v').toList()\n"
                            "              : '${e.value}',\n"
                            '    });\n'
                            '  }\n'
                            '\n'
                            '  /// Default headers + auth header + per-request headers (highest priority).\n'
                            '  ///\n'
                            '  /// For file bodies the default JSON `Content-Type` is replaced: multipart\n'
                            '  /// bodies get theirs (with boundary) from the transport, raw files use the\n'
                            "  /// file's MIME type.\n"
                            '  @protected\n'
                            '  Map<String, String> buildHeaders(Map<String, String>? extra,\n'
                            '      {Object? body}) {\n'
                            '    final headers = <String, String>{};\n'
                            '    _config.headers.forEach((k, v) => _setHeader(headers, k, v));\n'
                            '\n'
                            '    if (body is ApiFormData) {\n'
                            "      headers.removeWhere((k, _) => k.toLowerCase() == 'content-type');\n"
                            '    } else if (body is ApiFile) {\n'
                            "      _setHeader(headers, 'Content-Type', body.contentType);\n"
                            '    } else if (body is List<int>) {\n'
                            "      _setHeader(headers, 'Content-Type', 'application/octet-stream');\n"
                            '    }\n'
                            '\n'
                            '    final token = _authToken;\n'
                            '    if (token != null && token.isNotEmpty) {\n'
                            '      _setHeader(headers, _config.authHeaderKey,\n'
                            "          '${_config.authScheme} $token'.trim());\n"
                            '    }\n'
                            '    extra?.forEach((k, v) => _setHeader(headers, k, v));\n'
                            '    return headers;\n'
                            '  }\n'
                            '\n'
                            '  // ---------- Internals ----------\n'
                            '\n'
                            '  Future<T> _execute<T>(ApiRequest request, JsonParser<T>? parser) async {\n'
                            '    final stopwatch = Stopwatch()..start();\n'
                            '    _logger.logRequest(\n'
                            '        request.method, request.uri, request.headers, request.body);\n'
                            '\n'
                            '    final ApiResponse response;\n'
                            '    try {\n'
                            '      response = await send(request);\n'
                            '    } catch (e, st) {\n'
                            '      throw _fail(\n'
                            '        request,\n'
                            '        stopwatch,\n'
                            '        e is ApiException\n'
                            '            ? e\n'
                            '            : ApiException(\n'
                            '                type: ApiErrorType.unknown,\n'
                            "                message: e is UnsupportedError ? '${e.message}' : '$e',\n"
                            '                error: e,\n'
                            '                stackTrace: st,\n'
                            '              ),\n'
                            '      );\n'
                            '    }\n'
                            '\n'
                            '    if (!response.isSuccess) {\n'
                            '      throw _fail(\n'
                            '          request,\n'
                            '          stopwatch,\n'
                            '          ApiException.fromResponse(\n'
                            '              response.statusCode, _decodeErrorBody(response.data)));\n'
                            '    }\n'
                            '\n'
                            '    _logger.logResponse(request.method, request.uri, response.statusCode,\n'
                            '        response.data, stopwatch.elapsed);\n'
                            '\n'
                            '    try {\n'
                            '      return parser != null ? parser(response.data) : response.data as T;\n'
                            '    } catch (e, st) {\n'
                            '      throw _fail(\n'
                            '        request,\n'
                            '        stopwatch,\n'
                            '        ApiException(\n'
                            '          type: ApiErrorType.parse,\n'
                            "          message: 'Failed to parse response: $e',\n"
                            '          statusCode: response.statusCode,\n'
                            '          data: response.data,\n'
                            '          error: e,\n'
                            '          stackTrace: st,\n'
                            '        ),\n'
                            '      );\n'
                            '    }\n'
                            '  }\n'
                            '\n'
                            '  ApiException _fail(ApiRequest request, Stopwatch stopwatch, ApiException e) '
                            '{\n'
                            '    _logger.logError(request.method, request.uri, e, stopwatch.elapsed);\n'
                            '    return e;\n'
                            '  }\n'
                            '\n'
                            '  /// Error bodies of byte requests arrive as bytes; decode them so the\n'
                            "  /// server's error message can be read.\n"
                            '  static dynamic _decodeErrorBody(dynamic data) {\n'
                            '    if (data is! Uint8List) return data;\n'
                            '    if (data.isEmpty) return null;\n'
                            '    final text = utf8.decode(data, allowMalformed: true);\n'
                            '    try {\n'
                            '      return jsonDecode(text);\n'
                            '    } on FormatException {\n'
                            '      return text;\n'
                            '    }\n'
                            '  }\n'
                            '\n'
                            '  /// Sets a header, replacing any existing key that differs only in case.\n'
                            '  static void _setHeader(Map<String, String> headers, String key, String value) '
                            '{\n'
                            '    headers.removeWhere((k, _) => k.toLowerCase() == key.toLowerCase());\n'
                            '    headers[key] = value;\n'
                            '  }\n'
                            '\n'
                            '  static ApiLogger _createLogger(ApiConfig config) => ApiLogger(\n'
                            '        enabled: config.enableLogging,\n'
                            '        maxLength: config.maxLogLength,\n'
                            "        redactedHeaders: {'authorization', config.authHeaderKey},\n"
                            '      );\n'
                            '}\n',
 'lib/api/api_config.dart': "import 'package:flutter/foundation.dart';\n"
                            '\n'
                            '/// All settings needed to talk to a backend.\n'
                            '///\n'
                            '/// Create one per backend and pass it to [ApiManager.init] (or directly to a\n'
                            '/// [DioApiClient] / [HttpApiClient]).\n'
                            '@immutable\n'
                            'class ApiConfig {\n'
                            '  const ApiConfig({\n'
                            '    required this.baseUrl,\n'
                            '    this.headers = const {\n'
                            "      'Content-Type': 'application/json',\n"
                            "      'Accept': 'application/json',\n"
                            '    },\n'
                            '    this.connectTimeout = const Duration(seconds: 30),\n'
                            '    this.receiveTimeout = const Duration(seconds: 30),\n'
                            '    this.sendTimeout = const Duration(seconds: 30),\n'
                            '    this.authToken,\n'
                            "    this.authHeaderKey = 'Authorization',\n"
                            "    this.authScheme = 'Bearer',\n"
                            '    this.enableLogging = kDebugMode,\n'
                            '    this.maxLogLength = 4000,\n'
                            '  });\n'
                            '\n'
                            '  /// e.g. `https://api.example.com/v1`. Request paths are appended to this.\n'
                            '  final String baseUrl;\n'
                            '\n'
                            '  /// Default headers sent with every request.\n'
                            '  final Map<String, String> headers;\n'
                            '\n'
                            '  /// Time allowed to establish the connection.\n'
                            '  final Duration connectTimeout;\n'
                            '\n'
                            '  /// Longest allowed gap while receiving the response body, so large\n'
                            "  /// downloads don't time out as long as data keeps arriving.\n"
                            '  final Duration receiveTimeout;\n'
                            '\n'
                            '  /// Time allowed to upload the request body.\n'
                            '  ///\n'
                            '  /// The `http` package has no per-phase timeouts, so [HttpApiClient] waits\n'
                            '  /// up to connect + send + receive timeouts for the response headers.\n'
                            '  final Duration sendTimeout;\n'
                            '\n'
                            '  /// Initial auth token. Change it later with [ApiClient.setAuthToken].\n'
                            '  final String? authToken;\n'
                            '\n'
                            '  /// Header that carries the token.\n'
                            '  final String authHeaderKey;\n'
                            '\n'
                            "  /// Prefix before the token, e.g. `Bearer`. Use `''` to send the raw token.\n"
                            '  final String authScheme;\n'
                            '\n'
                            '  /// Print requests, responses and errors to the console.\n'
                            '  /// Defaults to on in debug builds only.\n'
                            '  final bool enableLogging;\n'
                            '\n'
                            '  /// Logged bodies longer than this are truncated.\n'
                            '  final int maxLogLength;\n'
                            '\n'
                            '  ApiConfig copyWith({\n'
                            '    String? baseUrl,\n'
                            '    Map<String, String>? headers,\n'
                            '    Duration? connectTimeout,\n'
                            '    Duration? receiveTimeout,\n'
                            '    Duration? sendTimeout,\n'
                            '    String? authToken,\n'
                            '    String? authHeaderKey,\n'
                            '    String? authScheme,\n'
                            '    bool? enableLogging,\n'
                            '    int? maxLogLength,\n'
                            '  }) {\n'
                            '    return ApiConfig(\n'
                            '      baseUrl: baseUrl ?? this.baseUrl,\n'
                            '      headers: headers ?? this.headers,\n'
                            '      connectTimeout: connectTimeout ?? this.connectTimeout,\n'
                            '      receiveTimeout: receiveTimeout ?? this.receiveTimeout,\n'
                            '      sendTimeout: sendTimeout ?? this.sendTimeout,\n'
                            '      authToken: authToken ?? this.authToken,\n'
                            '      authHeaderKey: authHeaderKey ?? this.authHeaderKey,\n'
                            '      authScheme: authScheme ?? this.authScheme,\n'
                            '      enableLogging: enableLogging ?? this.enableLogging,\n'
                            '      maxLogLength: maxLogLength ?? this.maxLogLength,\n'
                            '    );\n'
                            '  }\n'
                            '}\n',
 'lib/api/api_exception.dart': 'enum ApiErrorType {\n'
                               '  /// No connection, DNS failure, connection refused, bad certificate.\n'
                               '  network,\n'
                               '  timeout,\n'
                               '  cancelled,\n'
                               '\n'
                               '  /// 400\n'
                               '  badRequest,\n'
                               '\n'
                               '  /// 401\n'
                               '  unauthorized,\n'
                               '\n'
                               '  /// 403\n'
                               '  forbidden,\n'
                               '\n'
                               '  /// 404\n'
                               '  notFound,\n'
                               '\n'
                               '  /// Any other 4xx (or unexpected non-2xx) status.\n'
                               '  httpError,\n'
                               '\n'
                               '  /// 5xx\n'
                               '  server,\n'
                               '\n'
                               '  /// The response arrived but could not be converted by the parser.\n'
                               '  parse,\n'
                               '  unknown,\n'
                               '}\n'
                               '\n'
                               '/// The only exception type thrown by [ApiClient]. Catch this in your UI.\n'
                               'class ApiException implements Exception {\n'
                               '  ApiException({\n'
                               '    required this.type,\n'
                               '    required this.message,\n'
                               '    this.statusCode,\n'
                               '    this.data,\n'
                               '    this.error,\n'
                               '    this.stackTrace,\n'
                               '  });\n'
                               '\n'
                               '  /// Builds an exception from a non-2xx response.\n'
                               '  factory ApiException.fromResponse(int statusCode, dynamic data) {\n'
                               '    return ApiException(\n'
                               '      type: _typeForStatus(statusCode),\n'
                               '      message: _extractMessage(statusCode, data),\n'
                               '      statusCode: statusCode,\n'
                               '      data: data,\n'
                               '    );\n'
                               '  }\n'
                               '\n'
                               '  final ApiErrorType type;\n'
                               '\n'
                               '  /// Human-readable message, taken from the server response when possible.\n'
                               '  final String message;\n'
                               '  final int? statusCode;\n'
                               '\n'
                               '  /// Raw response body, if any.\n'
                               '  final dynamic data;\n'
                               '\n'
                               '  /// Underlying error (DioException, ClientException, TimeoutException, '
                               '...).\n'
                               '  final Object? error;\n'
                               '  final StackTrace? stackTrace;\n'
                               '\n'
                               '  bool get isNetworkError =>\n'
                               '      type == ApiErrorType.network || type == ApiErrorType.timeout;\n'
                               '\n'
                               '  static ApiErrorType _typeForStatus(int code) {\n'
                               '    if (code >= 500) return ApiErrorType.server;\n'
                               '    return switch (code) {\n'
                               '      400 => ApiErrorType.badRequest,\n'
                               '      401 => ApiErrorType.unauthorized,\n'
                               '      403 => ApiErrorType.forbidden,\n'
                               '      404 => ApiErrorType.notFound,\n'
                               '      408 => ApiErrorType.timeout,\n'
                               '      _ => ApiErrorType.httpError,\n'
                               '    };\n'
                               '  }\n'
                               '\n'
                               '  static String _extractMessage(int code, dynamic data) {\n'
                               '    if (data is Map) {\n'
                               "      for (final key in const ['message', 'error', 'detail', 'msg']) {\n"
                               '        final value = data[key];\n'
                               '        if (value is String && value.isNotEmpty) return value;\n'
                               '      }\n'
                               '    }\n'
                               '    if (data is String && data.isNotEmpty && data.length <= 200) return '
                               'data;\n'
                               "    return 'Request failed with status code $code';\n"
                               '  }\n'
                               '\n'
                               '  @override\n'
                               '  String toString() {\n'
                               "    final status = statusCode == null ? '' : ' $statusCode';\n"
                               "    return 'ApiException(${type.name}$status): $message';\n"
                               '  }\n'
                               '}\n',
 'lib/api/api_file.dart': "import 'dart:convert';\n"
                          '\n'
                          '/// A file to upload, either from a path on disk or from bytes in memory.\n'
                          '///\n'
                          '/// Use it as a value in [ApiFormData] (multipart upload), or pass it directly\n'
                          '/// as `body` to send the raw bytes (e.g. a PUT to a pre-signed storage URL).\n'
                          '///\n'
                          '/// [ApiFile.fromPath] is not available on Flutter Web. Use [ApiFile.fromBytes]\n'
                          "/// there (e.g. with bytes from `image_picker`'s `XFile.readAsBytes()`).\n"
                          'class ApiFile {\n'
                          '  ApiFile.fromPath(String this.path, {String? filename, String? contentType})\n'
                          '      : bytes = null,\n'
                          '        filename = filename ?? _basename(path),\n'
                          '        contentType = contentType ?? contentTypeFor(filename ?? path);\n'
                          '\n'
                          '  ApiFile.fromBytes(List<int> this.bytes,\n'
                          '      {required this.filename, String? contentType})\n'
                          '      : path = null,\n'
                          '        contentType = contentType ?? contentTypeFor(filename);\n'
                          '\n'
                          '  final String? path;\n'
                          '  final List<int>? bytes;\n'
                          '  final String filename;\n'
                          '\n'
                          '  /// MIME type, e.g. `image/jpeg`. Guessed from the file extension if omitted.\n'
                          '  final String contentType;\n'
                          '\n'
                          '  @override\n'
                          '  String toString() {\n'
                          "    final source = bytes != null ? '${bytes!.length} bytes' : path;\n"
                          "    return '$filename ($contentType, $source)';\n"
                          '  }\n'
                          '\n'
                          "  static String _basename(String path) => path.split(RegExp(r'[/\\\\]')).last;\n"
                          '\n'
                          '  /// Guesses a MIME type from a file name. Falls back to\n'
                          '  /// `application/octet-stream`.\n'
                          '  static String contentTypeFor(String filename) {\n'
                          "    final dot = filename.lastIndexOf('.');\n"
                          "    final ext = dot == -1 ? '' : filename.substring(dot + 1).toLowerCase();\n"
                          "    return _mimeTypes[ext] ?? 'application/octet-stream';\n"
                          '  }\n'
                          '\n'
                          '  static const _mimeTypes = {\n'
                          "    'jpg': 'image/jpeg',\n"
                          "    'jpeg': 'image/jpeg',\n"
                          "    'png': 'image/png',\n"
                          "    'gif': 'image/gif',\n"
                          "    'webp': 'image/webp',\n"
                          "    'bmp': 'image/bmp',\n"
                          "    'heic': 'image/heic',\n"
                          "    'heif': 'image/heif',\n"
                          "    'svg': 'image/svg+xml',\n"
                          "    'ico': 'image/x-icon',\n"
                          "    'mp4': 'video/mp4',\n"
                          "    'mov': 'video/quicktime',\n"
                          "    'webm': 'video/webm',\n"
                          "    'mkv': 'video/x-matroska',\n"
                          "    'mp3': 'audio/mpeg',\n"
                          "    'm4a': 'audio/mp4',\n"
                          "    'aac': 'audio/aac',\n"
                          "    'wav': 'audio/wav',\n"
                          "    'ogg': 'audio/ogg',\n"
                          "    'pdf': 'application/pdf',\n"
                          "    'json': 'application/json',\n"
                          "    'zip': 'application/zip',\n"
                          "    'txt': 'text/plain',\n"
                          "    'csv': 'text/csv',\n"
                          "    'html': 'text/html',\n"
                          "    'xml': 'application/xml',\n"
                          "    'doc': 'application/msword',\n"
                          "    'docx':\n"
                          '        '
                          "'application/vnd.openxmlformats-officedocument.wordprocessingml.document',\n"
                          "    'xls': 'application/vnd.ms-excel',\n"
                          "    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',\n"
                          "    'ppt': 'application/vnd.ms-powerpoint',\n"
                          "    'pptx':\n"
                          '        '
                          "'application/vnd.openxmlformats-officedocument.presentationml.presentation',\n"
                          '  };\n'
                          '}\n'
                          '\n'
                          '/// A `multipart/form-data` body: text fields plus files.\n'
                          '///\n'
                          '/// ```dart\n'
                          "/// await api.post('/profile', body: ApiFormData.fromMap({\n"
                          "///   'name': 'Ana',\n"
                          "///   'avatar': ApiFile.fromPath(image.path),\n"
                          "///   'photos': [ApiFile.fromPath(a), ApiFile.fromPath(b)],\n"
                          '/// }));\n'
                          '/// ```\n'
                          'class ApiFormData {\n'
                          '  ApiFormData();\n'
                          '\n'
                          '  /// Values may be an [ApiFile], a list of [ApiFile]s, or anything else.\n'
                          '  /// Maps and lists are sent as JSON strings, other values via `toString()`.\n'
                          '  /// Null values are skipped.\n'
                          '  factory ApiFormData.fromMap(Map<String, dynamic> map) {\n'
                          '    final form = ApiFormData();\n'
                          '    map.forEach((key, value) {\n'
                          '      if (value == null) return;\n'
                          '      if (value is ApiFile) {\n'
                          '        form.addFile(key, value);\n'
                          '      } else if (value is Iterable<ApiFile>) {\n'
                          '        for (final file in value) {\n'
                          '          form.addFile(key, file);\n'
                          '        }\n'
                          '      } else {\n'
                          '        form.addField(\n'
                          '            key,\n'
                          '            value is String\n'
                          '                ? value\n'
                          '                : (value is Map || value is Iterable)\n'
                          '                    ? jsonEncode(value)\n'
                          "                    : '$value');\n"
                          '      }\n'
                          '    });\n'
                          '    return form;\n'
                          '  }\n'
                          '\n'
                          '  /// Note: [HttpApiClient] keeps only the last value if a field name repeats.\n'
                          '  /// Repeated file field names work on both clients.\n'
                          '  final List<MapEntry<String, String>> fields = [];\n'
                          '  final List<MapEntry<String, ApiFile>> files = [];\n'
                          '\n'
                          '  void addField(String name, String value) => fields.add(MapEntry(name, value));\n'
                          '\n'
                          '  void addFile(String name, ApiFile file) => files.add(MapEntry(name, file));\n'
                          '}\n',
 'lib/api/api_logger.dart': "import 'dart:convert';\n"
                            '\n'
                            "import 'package:flutter/foundation.dart';\n"
                            '\n'
                            "import 'api_client.dart';\n"
                            "import 'api_exception.dart';\n"
                            "import 'api_file.dart';\n"
                            '\n'
                            '/// Prints requests, responses and errors to the console.\n'
                            '/// Values of sensitive headers (such as the auth header) are masked.\n'
                            'class ApiLogger {\n'
                            '  ApiLogger({\n'
                            '    this.enabled = true,\n'
                            '    this.maxLength = 4000,\n'
                            "    Set<String> redactedHeaders = const {'authorization'},\n"
                            '  }) : _redactedHeaders = redactedHeaders.map((h) => h.toLowerCase()).toSet();\n'
                            '\n'
                            '  final bool enabled;\n'
                            '  final int maxLength;\n'
                            '  final Set<String> _redactedHeaders;\n'
                            '\n'
                            '  void logRequest(\n'
                            '    HttpMethod method,\n'
                            '    Uri uri,\n'
                            '    Map<String, String> headers,\n'
                            '    Object? body,\n'
                            '  ) {\n'
                            "    _print('REQUEST', [\n"
                            "      '${method.value} $uri',\n"
                            "      'Headers: ${_redact(headers)}',\n"
                            "      if (body != null) 'Body: ${_format(body)}',\n"
                            '    ]);\n'
                            '  }\n'
                            '\n'
                            '  void logResponse(\n'
                            '    HttpMethod method,\n'
                            '    Uri uri,\n'
                            '    int statusCode,\n'
                            '    dynamic data,\n'
                            '    Duration elapsed,\n'
                            '  ) {\n'
                            "    _print('RESPONSE', [\n"
                            "      '${method.value} $uri',\n"
                            "      'Status: $statusCode (${elapsed.inMilliseconds} ms)',\n"
                            "      'Data: ${_format(data)}',\n"
                            '    ]);\n'
                            '  }\n'
                            '\n'
                            '  void logError(\n'
                            '    HttpMethod method,\n'
                            '    Uri uri,\n'
                            '    ApiException exception,\n'
                            '    Duration elapsed,\n'
                            '  ) {\n'
                            "    _print('ERROR', [\n"
                            "      '${method.value} $uri',\n"
                            "      'Type: ${exception.type.name}'\n"
                            "          '${exception.statusCode == null ? '' : ' | Status: "
                            "${exception.statusCode}'}'\n"
                            "          ' (${elapsed.inMilliseconds} ms)',\n"
                            "      'Message: ${exception.message}',\n"
                            "      if (exception.data != null) 'Data: ${_format(exception.data)}',\n"
                            '    ]);\n'
                            '  }\n'
                            '\n'
                            '  void _print(String title, List<String> lines) {\n'
                            '    if (!enabled) return;\n'
                            "    debugPrint('┌─── API $title ───────────────────────────');\n"
                            '    for (final line in lines) {\n'
                            "      for (final part in line.split('\\n')) {\n"
                            "        debugPrint('│ $part');\n"
                            '      }\n'
                            '    }\n'
                            "    debugPrint('└──────────────────────────────────────────');\n"
                            '  }\n'
                            '\n'
                            '  Map<String, String> _redact(Map<String, String> headers) => {\n'
                            '        for (final e in headers.entries)\n'
                            "          e.key: _redactedHeaders.contains(e.key.toLowerCase()) ? '***' : "
                            'e.value,\n'
                            '      };\n'
                            '\n'
                            '  String _format(Object? data) {\n'
                            '    String text;\n'
                            '    if (data is ApiFormData) {\n'
                            '      text = [\n'
                            "        for (final f in data.fields) '${f.key}: ${f.value}',\n"
                            "        for (final f in data.files) '${f.key}: [file] ${f.value}',\n"
                            "      ].join('\\n');\n"
                            '    } else if (data is ApiFile) {\n'
                            "      text = '[file] $data';\n"
                            '    } else if (data is List<int>) {\n'
                            '      // Raw bytes (uploads or ApiResponseType.bytes responses), not JSON.\n'
                            "      text = '<binary, ${data.length} bytes>';\n"
                            '    } else if (data is Map || data is List) {\n'
                            '      try {\n'
                            "        text = const JsonEncoder.withIndent('  ').convert(data);\n"
                            '      } catch (_) {\n'
                            '        text = data.toString();\n'
                            '      }\n'
                            '    } else {\n'
                            "      text = '$data';\n"
                            '    }\n'
                            '    if (text.length <= maxLength) return text;\n'
                            "    return '${text.substring(0, maxLength)}… (${text.length - maxLength} more "
                            "chars)';\n"
                            '  }\n'
                            '}\n',
 'lib/api/api_manager.dart': "import 'api_client.dart';\n"
                             "import 'api_config.dart';\n"
                             "import 'dio_api_client.dart';\n"
                             "import 'http_api_client.dart';\n"
                             '\n'
                             'enum ApiClientType { dio, http }\n'
                             '\n'
                             '/// App-wide access point. Call [init] once in `main()`, then use\n'
                             '/// [ApiManager.client] anywhere.\n'
                             '///\n'
                             '/// ```dart\n'
                             "/// ApiManager.init(const ApiConfig(baseUrl: 'https://api.example.com'));\n"
                             "/// final users = await ApiManager.client.get('/users');\n"
                             '/// ```\n'
                             'class ApiManager {\n'
                             '  ApiManager._();\n'
                             '\n'
                             '  static ApiClient? _client;\n'
                             '\n'
                             '  /// Creates the shared client. Calling it again replaces (and closes) the\n'
                             '  /// previous one.\n'
                             '  static ApiClient init(\n'
                             '    ApiConfig config, {\n'
                             '    ApiClientType type = ApiClientType.dio,\n'
                             '  }) {\n'
                             '    _client?.close();\n'
                             '    return _client = switch (type) {\n'
                             '      ApiClientType.dio => DioApiClient(config),\n'
                             '      ApiClientType.http => HttpApiClient(config),\n'
                             '    };\n'
                             '  }\n'
                             '\n'
                             '  static ApiClient get client {\n'
                             '    final client = _client;\n'
                             '    if (client == null) {\n'
                             '      throw StateError(\n'
                             "          'ApiManager.init(...) must be called before using "
                             "ApiManager.client.');\n"
                             '    }\n'
                             '    return client;\n'
                             '  }\n'
                             '\n'
                             '  static void setAuthToken(String? token) => client.setAuthToken(token);\n'
                             '}\n',
 'lib/api/dio_api_client.dart': "import 'dart:typed_data';\n"
                                '\n'
                                "import 'package:dio/dio.dart';\n"
                                '\n'
                                "import 'api_client.dart';\n"
                                "import 'api_exception.dart';\n"
                                "import 'api_file.dart';\n"
                                '\n'
                                '/// [ApiClient] backed by `package:dio`.\n'
                                '///\n'
                                '/// The underlying [dio] instance is public, so you can add your own\n'
                                '/// interceptors (e.g. token refresh), or use any other Dio feature '
                                'directly.\n'
                                'class DioApiClient extends ApiClient {\n'
                                '  DioApiClient(super.config, {Dio? dio}) : dio = dio ?? Dio() {\n'
                                '    _applyOptions();\n'
                                '  }\n'
                                '\n'
                                '  final Dio dio;\n'
                                '\n'
                                '  static const _responseTypes = {\n'
                                '    ApiResponseType.json: ResponseType.json,\n'
                                '    ApiResponseType.text: ResponseType.plain,\n'
                                '    ApiResponseType.bytes: ResponseType.bytes,\n'
                                '  };\n'
                                '\n'
                                '  @override\n'
                                '  Future<ApiResponse> send(ApiRequest request) async {\n'
                                '    try {\n'
                                '      final (data, contentLength) = await _toDioData(request.body);\n'
                                '      final options = Options(\n'
                                '        method: request.method.value,\n'
                                '        headers: {\n'
                                '          ...request.headers,\n'
                                '          if (contentLength != null) Headers.contentLengthHeader: '
                                "'$contentLength',\n"
                                '        },\n'
                                '        // Dio warns if sendTimeout is set on a request without a body.\n'
                                '        sendTimeout: data != null ? config.sendTimeout : null,\n'
                                '        responseType: _responseTypes[request.responseType],\n'
                                '        // Status codes are checked in ApiClient, so accept them all here.\n'
                                '        // Downloads only accept 2xx, so an error page is never saved to '
                                'disk.\n'
                                '        validateStatus: request.savePath == null\n'
                                '            ? (_) => true\n'
                                '            : (status) => status != null && status >= 200 && status < 300,\n'
                                '      );\n'
                                '\n'
                                '      final savePath = request.savePath;\n'
                                '      if (savePath != null) {\n'
                                '        final response = await dio.downloadUri(\n'
                                '          request.uri,\n'
                                '          savePath,\n'
                                '          options: options,\n'
                                '          onReceiveProgress: request.onReceiveProgress,\n'
                                '        );\n'
                                '        return ApiResponse(\n'
                                '          statusCode: response.statusCode ?? 0,\n'
                                '          data: savePath,\n'
                                '          headers: _headers(response),\n'
                                '        );\n'
                                '      }\n'
                                '\n'
                                '      final response = await dio.requestUri<dynamic>(\n'
                                '        request.uri,\n'
                                '        data: data,\n'
                                '        options: options,\n'
                                '        onSendProgress: request.onSendProgress,\n'
                                '        onReceiveProgress: request.onReceiveProgress,\n'
                                '      );\n'
                                '      return ApiResponse(\n'
                                '        statusCode: response.statusCode ?? 0,\n'
                                '        data: _normalize(response.data, request.responseType),\n'
                                '        headers: _headers(response),\n'
                                '      );\n'
                                '    } on DioException catch (e, st) {\n'
                                '      throw _mapDioException(e, st);\n'
                                '    }\n'
                                '  }\n'
                                '\n'
                                '  @override\n'
                                '  void onConfigChanged() => _applyOptions();\n'
                                '\n'
                                '  @override\n'
                                '  void close() => dio.close();\n'
                                '\n'
                                '  void _applyOptions() {\n'
                                '    dio.options\n'
                                '      ..baseUrl = config.baseUrl\n'
                                '      ..connectTimeout = config.connectTimeout\n'
                                '      ..receiveTimeout = config.receiveTimeout;\n'
                                '  }\n'
                                '\n'
                                '  /// Converts our body types into what Dio expects.\n'
                                '  /// Returns the data and, for streams, its length.\n'
                                '  Future<(Object?, int?)> _toDioData(Object? body) async {\n'
                                '    if (body is ApiFormData) {\n'
                                '      final form = FormData()..fields.addAll(body.fields);\n'
                                '      for (final file in body.files) {\n'
                                '        form.files.add(MapEntry(file.key, await '
                                '_toMultipartFile(file.value)));\n'
                                '      }\n'
                                '      return (form, null);\n'
                                '    }\n'
                                '    if (body is ApiFile) {\n'
                                '      final file = await _toMultipartFile(body);\n'
                                '      return (file.finalize(), file.length);\n'
                                '    }\n'
                                '    // Dio sends only Uint8List as raw bytes; other List<int>s would be\n'
                                '    // JSON-encoded.\n'
                                '    if (body is List<int> && body is! Uint8List) {\n'
                                '      return (Uint8List.fromList(body), null);\n'
                                '    }\n'
                                '    return (body, null);\n'
                                '  }\n'
                                '\n'
                                '  Future<MultipartFile> _toMultipartFile(ApiFile file) {\n'
                                '    final contentType = DioMediaType.parse(file.contentType);\n'
                                '    final bytes = file.bytes;\n'
                                '    if (bytes != null) {\n'
                                '      return Future.value(MultipartFile.fromBytes(bytes,\n'
                                '          filename: file.filename, contentType: contentType));\n'
                                '    }\n'
                                '    return MultipartFile.fromFile(file.path!,\n'
                                '        filename: file.filename, contentType: contentType);\n'
                                '  }\n'
                                '\n'
                                "  /// Makes Dio's output match [HttpApiClient] for the same response type.\n"
                                '  dynamic _normalize(dynamic data, ApiResponseType type) {\n'
                                '    if (type == ApiResponseType.bytes && data is List<int> && data is! '
                                'Uint8List) {\n'
                                '      return Uint8List.fromList(data);\n'
                                '    }\n'
                                '    if (type == ApiResponseType.json && data is String && data.isEmpty) {\n'
                                '      return null;\n'
                                '    }\n'
                                '    return data;\n'
                                '  }\n'
                                '\n'
                                '  Map<String, String> _headers(Response<dynamic> response) => response\n'
                                '      .headers.map\n'
                                "      .map((key, values) => MapEntry(key, values.join(', ')));\n"
                                '\n'
                                '  ApiException _mapDioException(DioException e, StackTrace st) {\n'
                                '    final response = e.response;\n'
                                '    if (e.type == DioExceptionType.badResponse && response != null) {\n'
                                '      return ApiException.fromResponse(response.statusCode ?? 0, '
                                'response.data);\n'
                                '    }\n'
                                '\n'
                                '    final (type, message) = switch (e.type) {\n'
                                '      DioExceptionType.connectionTimeout => (\n'
                                '          ApiErrorType.timeout,\n'
                                "          'Connection timed out after ${config.connectTimeout.inSeconds}s'\n"
                                '        ),\n'
                                '      DioExceptionType.sendTimeout => (\n'
                                '          ApiErrorType.timeout,\n'
                                "          'Sending the request timed out'\n"
                                '        ),\n'
                                '      DioExceptionType.receiveTimeout => (\n'
                                '          ApiErrorType.timeout,\n'
                                "          'Receiving the response timed out'\n"
                                '        ),\n'
                                '      DioExceptionType.cancel => (\n'
                                '          ApiErrorType.cancelled,\n'
                                "          'Request was cancelled'\n"
                                '        ),\n'
                                '      DioExceptionType.connectionError => (\n'
                                '          ApiErrorType.network,\n'
                                "          'No internet connection or the server could not be reached'\n"
                                '        ),\n'
                                '      DioExceptionType.badCertificate => (\n'
                                '          ApiErrorType.network,\n'
                                "          'Bad SSL certificate'\n"
                                '        ),\n'
                                '      _ => (ApiErrorType.unknown, e.message ?? e.error?.toString() ?? '
                                "'$e'),\n"
                                '    };\n'
                                '\n'
                                '    return ApiException(\n'
                                '      type: type,\n'
                                '      message: message,\n'
                                '      error: e,\n'
                                '      stackTrace: st,\n'
                                '    );\n'
                                '  }\n'
                                '}\n',
 'lib/api/file_writer/file_writer.dart': '// Picks the dart:io implementation on mobile/desktop and a stub '
                                         'on web.\n'
                                         "export 'file_writer_stub.dart' if (dart.library.io) "
                                         "'file_writer_io.dart';\n",
 'lib/api/file_writer/file_writer_io.dart': "import 'dart:io';\n"
                                            '\n'
                                            '/// Streams [stream] into the file at [path], creating parent '
                                            'folders.\n'
                                            '/// A partially written file is deleted if the stream fails.\n'
                                            'Future<void> writeStreamToFile(Stream<List<int>> stream, String '
                                            'path) async {\n'
                                            '  final file = File(path);\n'
                                            '  await file.parent.create(recursive: true);\n'
                                            '  final sink = file.openWrite();\n'
                                            '  try {\n'
                                            '    await sink.addStream(stream);\n'
                                            '    await sink.close();\n'
                                            '  } catch (_) {\n'
                                            '    await sink.close().catchError((_) {});\n'
                                            '    if (await file.exists()) await file.delete();\n'
                                            '    rethrow;\n'
                                            '  }\n'
                                            '}\n',
 'lib/api/file_writer/file_writer_stub.dart': '/// Web fallback: there is no file system to save to.\n'
                                              'Future<void> writeStreamToFile(Stream<List<int>> stream, '
                                              'String path) {\n'
                                              '  throw UnsupportedError(\n'
                                              "      'Saving downloads to a file path is not supported on "
                                              "this platform. '\n"
                                              "      'Use get(..., responseType: ApiResponseType.bytes) "
                                              "instead.');\n"
                                              '}\n',
 'lib/api/http_api_client.dart': "import 'dart:async';\n"
                                 "import 'dart:convert';\n"
                                 "import 'dart:typed_data';\n"
                                 '\n'
                                 "import 'package:http/http.dart' as http;\n"
                                 "import 'package:http_parser/http_parser.dart';\n"
                                 '\n'
                                 "import 'api_client.dart';\n"
                                 "import 'api_exception.dart';\n"
                                 "import 'api_file.dart';\n"
                                 "import 'file_writer/file_writer.dart';\n"
                                 '\n'
                                 '/// [ApiClient] backed by `package:http`.\n'
                                 'class HttpApiClient extends ApiClient {\n'
                                 '  HttpApiClient(super.config, {http.Client? client})\n'
                                 '      : _client = client ?? http.Client();\n'
                                 '\n'
                                 '  final http.Client _client;\n'
                                 '\n'
                                 '  @override\n'
                                 '  Future<ApiResponse> send(ApiRequest request) async {\n'
                                 '    try {\n'
                                 '      var httpRequest = await _buildRequest(request);\n'
                                 '      final onSendProgress = request.onSendProgress;\n'
                                 '      if (onSendProgress != null) {\n'
                                 '        httpRequest = _withSendProgress(httpRequest, onSendProgress);\n'
                                 '      }\n'
                                 '\n'
                                 '      final response =\n'
                                 '          await '
                                 '_client.send(httpRequest).timeout(_responseTimeout(request));\n'
                                 '\n'
                                 '      // receiveTimeout = the longest allowed gap between incoming '
                                 'chunks.\n'
                                 '      final body = _withReceiveProgress(\n'
                                 '        response.stream.timeout(config.receiveTimeout),\n'
                                 '        response.contentLength,\n'
                                 '        request.onReceiveProgress,\n'
                                 '      );\n'
                                 '\n'
                                 '      final savePath = request.savePath;\n'
                                 '      final isSuccess = response.statusCode >= 200 && response.statusCode '
                                 '< 300;\n'
                                 '      if (savePath != null && isSuccess) {\n'
                                 '        await writeStreamToFile(body, savePath);\n'
                                 '        return ApiResponse(\n'
                                 '          statusCode: response.statusCode,\n'
                                 '          data: savePath,\n'
                                 '          headers: response.headers,\n'
                                 '        );\n'
                                 '      }\n'
                                 '\n'
                                 '      final bytes = await http.ByteStream(body).toBytes();\n'
                                 '      return ApiResponse(\n'
                                 '        statusCode: response.statusCode,\n'
                                 '        data: _decode(bytes, request.responseType),\n'
                                 '        headers: response.headers,\n'
                                 '      );\n'
                                 '    } on TimeoutException catch (e, st) {\n'
                                 '      throw ApiException(\n'
                                 '        type: ApiErrorType.timeout,\n'
                                 "        message: 'Request timed out after ${e.duration?.inSeconds}s',\n"
                                 '        error: e,\n'
                                 '        stackTrace: st,\n'
                                 '      );\n'
                                 '    } on http.ClientException catch (e, st) {\n'
                                 '      throw ApiException(\n'
                                 '        type: ApiErrorType.network,\n'
                                 '        message: e.message,\n'
                                 '        error: e,\n'
                                 '        stackTrace: st,\n'
                                 '      );\n'
                                 '    }\n'
                                 '  }\n'
                                 '\n'
                                 '  @override\n'
                                 '  void close() => _client.close();\n'
                                 '\n'
                                 '  /// Time allowed until the response headers arrive.\n'
                                 '  Duration _responseTimeout(ApiRequest request) =>\n'
                                 '      config.connectTimeout +\n'
                                 '      config.receiveTimeout +\n'
                                 '      (request.body != null ? config.sendTimeout : Duration.zero);\n'
                                 '\n'
                                 '  Future<http.BaseRequest> _buildRequest(ApiRequest request) async {\n'
                                 '    final method = request.method.value;\n'
                                 '    final body = request.body;\n'
                                 '\n'
                                 '    if (body is ApiFormData) {\n'
                                 '      // MultipartRequest sets its own Content-Type with the boundary.\n'
                                 '      final multipart = http.MultipartRequest(method, request.uri)\n'
                                 '        ..headers.addAll(request.headers);\n'
                                 '      for (final field in body.fields) {\n'
                                 '        multipart.fields[field.key] = field.value;\n'
                                 '      }\n'
                                 '      for (final file in body.files) {\n'
                                 '        multipart.files.add(await _toMultipartFile(file.key, '
                                 'file.value));\n'
                                 '      }\n'
                                 '      return multipart;\n'
                                 '    }\n'
                                 '\n'
                                 '    final httpRequest = http.Request(method, request.uri)\n'
                                 '      ..headers.addAll(request.headers);\n'
                                 '    if (body == null) return httpRequest;\n'
                                 '\n'
                                 '    if (body is String) {\n'
                                 '      httpRequest.body = body;\n'
                                 '    } else if (body is List<int>) {\n'
                                 '      httpRequest.bodyBytes = body;\n'
                                 '    } else if (body is ApiFile) {\n'
                                 '      httpRequest.bodyBytes = await _readFile(body);\n'
                                 '    } else {\n'
                                 '      httpRequest.body = jsonEncode(body);\n'
                                 '    }\n'
                                 '    return httpRequest;\n'
                                 '  }\n'
                                 '\n'
                                 '  Future<http.MultipartFile> _toMultipartFile(String field, ApiFile file) '
                                 '{\n'
                                 '    final contentType = MediaType.parse(file.contentType);\n'
                                 '    final bytes = file.bytes;\n'
                                 '    if (bytes != null) {\n'
                                 '      return Future.value(http.MultipartFile.fromBytes(field, bytes,\n'
                                 '          filename: file.filename, contentType: contentType));\n'
                                 '    }\n'
                                 '    return http.MultipartFile.fromPath(field, file.path!,\n'
                                 '        filename: file.filename, contentType: contentType);\n'
                                 '  }\n'
                                 '\n'
                                 '  Future<List<int>> _readFile(ApiFile file) async {\n'
                                 '    final bytes = file.bytes;\n'
                                 '    if (bytes != null) return bytes;\n'
                                 "    // Uses http's own platform-specific file reading.\n"
                                 "    final multipartFile = await _toMultipartFile('file', file);\n"
                                 '    return multipartFile.finalize().toBytes();\n'
                                 '  }\n'
                                 '\n'
                                 '  /// Re-sends [original] as a stream so upload progress can be reported.\n'
                                 '  http.BaseRequest _withSendProgress(\n'
                                 '      http.BaseRequest original, ApiProgressCallback onProgress) {\n'
                                 '    final total = original.contentLength;\n'
                                 '    final source = original.finalize();\n'
                                 '    final streamed = http.StreamedRequest(original.method, original.url)\n'
                                 '      ..headers.addAll(original.headers)\n'
                                 '      ..contentLength = total;\n'
                                 '\n'
                                 '    var sent = 0;\n'
                                 '    source.listen(\n'
                                 '      (chunk) {\n'
                                 '        sent += chunk.length;\n'
                                 '        onProgress(sent, total ?? -1);\n'
                                 '        streamed.sink.add(chunk);\n'
                                 '      },\n'
                                 '      onError: streamed.sink.addError,\n'
                                 '      onDone: streamed.sink.close,\n'
                                 '      cancelOnError: true,\n'
                                 '    );\n'
                                 '    return streamed;\n'
                                 '  }\n'
                                 '\n'
                                 '  Stream<List<int>> _withReceiveProgress(\n'
                                 '    Stream<List<int>> stream,\n'
                                 '    int? total,\n'
                                 '    ApiProgressCallback? onProgress,\n'
                                 '  ) {\n'
                                 '    if (onProgress == null) return stream;\n'
                                 '    var received = 0;\n'
                                 '    return stream.map((chunk) {\n'
                                 '      received += chunk.length;\n'
                                 '      onProgress(received, total ?? -1);\n'
                                 '      return chunk;\n'
                                 '    });\n'
                                 '  }\n'
                                 '\n'
                                 '  dynamic _decode(Uint8List bytes, ApiResponseType type) {\n'
                                 '    switch (type) {\n'
                                 '      case ApiResponseType.bytes:\n'
                                 '        return bytes;\n'
                                 '      case ApiResponseType.text:\n'
                                 '        return utf8.decode(bytes, allowMalformed: true);\n'
                                 '      case ApiResponseType.json:\n'
                                 '        if (bytes.isEmpty) return null;\n'
                                 '        final text = utf8.decode(bytes, allowMalformed: true);\n'
                                 '        try {\n'
                                 '          return jsonDecode(text);\n'
                                 '        } on FormatException {\n'
                                 '          return text;\n'
                                 '        }\n'
                                 '    }\n'
                                 '  }\n'
                                 '}\n',
 'lib/api/README.md': '# API layer\r\n'
                      '\r\n'
                      'A drop-in API folder for Flutter, with Dio and `http` behind one interface.\r\n'
                      '\r\n'
                      '## Setup\r\n'
                      '\r\n'
                      '1. Copy this `api/` folder into `lib/`.\r\n'
                      '2. Add the dependencies:\r\n'
                      '   ```yaml\r\n'
                      '   dependencies:\r\n'
                      '     dio: ^5.9.0\r\n'
                      '     http: ^1.6.0\r\n'
                      '     http_parser: ^4.1.2\r\n'
                      '   ```\r\n'
                      '3. Initialise it once in `main()`:\r\n'
                      '   ```dart\r\n'
                      "   import 'package:your_app/api/api.dart';\r\n"
                      '\r\n'
                      '   void main() {\r\n'
                      '     ApiManager.init(\r\n'
                      "       const ApiConfig(baseUrl: 'https://api.example.com'),\r\n"
                      '       type: ApiClientType.dio, // or ApiClientType.http\r\n'
                      '     );\r\n'
                      '     runApp(const MyApp());\r\n'
                      '   }\r\n'
                      '   ```\r\n'
                      '\r\n'
                      '## Usage\r\n'
                      '\r\n'
                      '```dart\r\n'
                      'final api = ApiManager.client;\r\n'
                      '\r\n'
                      '// Raw JSON\r\n'
                      "final json = await api.get('/users', query: {'page': 1});\r\n"
                      '\r\n'
                      '// Typed result\r\n'
                      'final users = await api.get(\r\n'
                      "  '/users',\r\n"
                      '  parser: (json) => (json as List).map((e) => User.fromJson(e)).toList(),\r\n'
                      '  <!-- parser: (json) => LoginModel.fromJson(json as Map<String, dynamic>) -->\r\n'
                      '  <!-- parser: (json) => (json as List).map((e) => DetaModel.fromJson(e as '
                      'Map<String, dynamic>).toList(), -->\r\n'
                      ');\r\n'
                      '\r\n'
                      '// Maps and lists are sent as JSON\r\n'
                      "await api.post('/users', body: {'name': 'Ana'});\r\n"
                      '\r\n'
                      '// Auth: the token is added to every request as `Authorization: Bearer <token>`\r\n'
                      'ApiManager.setAuthToken(token); // after login\r\n'
                      'ApiManager.setAuthToken(null);  // on logout\r\n'
                      '\r\n'
                      '// Errors\r\n'
                      'try {\r\n'
                      "  await api.delete('/users/1');\r\n"
                      '} on ApiException catch (e) {\r\n'
                      '  if (e.type == ApiErrorType.unauthorized) { /* go to login */ }\r\n'
                      '  if (e.isNetworkError) { /* show offline message */ }\r\n'
                      "  print(e.message); // taken from the server's `message`/`error` field when "
                      'present\r\n'
                      '}\r\n'
                      '```\r\n'
                      '\r\n'
                      '## Files and other data types\r\n'
                      '\r\n'
                      '| `body` value | Sent as |\r\n'
                      '| --- | --- |\r\n'
                      '| `Map` / `List` / other objects | JSON |\r\n'
                      '| `String` | Text, unchanged |\r\n'
                      '| `List<int>` / `Uint8List` | Raw bytes (`application/octet-stream`) |\r\n'
                      "| `ApiFile` | The file's raw bytes, with its MIME type (e.g. a PUT to a pre-signed "
                      'storage URL) |\r\n'
                      '| `ApiFormData` | `multipart/form-data`: text fields plus files |\r\n'
                      '\r\n'
                      '```dart\r\n'
                      '// Upload images and files with form fields, and track progress\r\n'
                      'await api.post(\r\n'
                      "  '/profile',\r\n"
                      '  body: ApiFormData.fromMap({\r\n'
                      "    'name': 'Ana',\r\n"
                      "    'avatar': ApiFile.fromPath(image.path),                   // mobile/desktop\r\n"
                      "    'cover': ApiFile.fromBytes(bytes, filename: 'cover.jpg'), // also works on web\r\n"
                      "    'photos': [ApiFile.fromPath(a), ApiFile.fromPath(b)],     // several files, one "
                      'field\r\n'
                      '  }),\r\n'
                      "  onSendProgress: (sent, total) => print('${sent * 100 ~/ total}%'),\r\n"
                      ');\r\n'
                      '\r\n'
                      '// Get an image or other binary file in memory\r\n'
                      "final Uint8List bytes = await api.get('/avatar.png', responseType: "
                      'ApiResponseType.bytes);\r\n'
                      '\r\n'
                      '// Stream a download straight to disk (not available on web)\r\n'
                      "await api.download('/report.pdf', '${dir.path}/report.pdf',\r\n"
                      '    onReceiveProgress: (received, total) { /* total is -1 if unknown */ });\r\n'
                      '```\r\n'
                      '\r\n'
                      'The MIME type is guessed from the file extension. Pass `contentType:` to `ApiFile` to '
                      'override it.\r\n'
                      'If a download fails, the partly written file is deleted.\r\n'
                      '\r\n'
                      '## Config options (`ApiConfig`)\r\n'
                      '\r\n'
                      '| Option | Default | Notes |\r\n'
                      '| --- | --- | --- |\r\n'
                      '| `baseUrl` | required | Request paths are appended to this. An absolute URL path '
                      'skips it. |\r\n'
                      '| `headers` | JSON content type | Sent with every request. Can be overridden per '
                      'request. |\r\n'
                      '| `connectTimeout` / `sendTimeout` | 30s | The `http` client waits up to connect + '
                      'send + receive for the response headers. |\r\n'
                      '| `receiveTimeout` | 30s | Longest allowed gap between incoming chunks, so large '
                      "downloads don't time out while data keeps arriving. |\r\n"
                      '| `authToken`, `authHeaderKey`, `authScheme` | `null`, `Authorization`, `Bearer` | '
                      "Use `authScheme: ''` to send the raw token. |\r\n"
                      '| `enableLogging` | `kDebugMode` | Logs requests, responses and errors. The auth '
                      'header is masked. |\r\n'
                      '| `maxLogLength` | 4000 | Longer logged bodies are truncated. |\r\n'
                      '\r\n'
                      'To change settings at runtime, use `client.updateConfig(config.copyWith(...))`.\r\n'
                      '\r\n'
                      '## Files\r\n'
                      '\r\n'
                      '- `api.dart`: barrel export (import only this file)\r\n'
                      '- `api_manager.dart`: global init and access\r\n'
                      '- `api_client.dart`: shared interface. Handles URLs, headers, auth, logging, status '
                      'checks and parsing.\r\n'
                      '- `dio_api_client.dart` / `http_api_client.dart`: the transport implementations\r\n'
                      '- `api_file.dart`: `ApiFile` and `ApiFormData` for uploads\r\n'
                      '- `file_writer/`: saves downloads to disk (with a web stub)\r\n'
                      '- `api_config.dart`, `api_exception.dart`, `api_logger.dart`\r\n'
                      '\r\n'
                      'For other Dio features (interceptors, token refresh, cancel tokens), use\r\n'
                      '`(ApiManager.client as DioApiClient).dio`.\r\n'}

def dart_string(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'").replace('$', '\\$').replace('\r', '\\r').replace('\n', '\\n') + "'"

def ask(label, default):
    return input(f'{label} [{default}]: ').strip() or default

def run(command, cwd=None):
    print('\n>', subprocess.list2cmdline([str(x) for x in command]), flush=True)
    subprocess.run(command, cwd=cwd, check=True)

def templates(name, manager, base_url, description, transport='dio'):
    files = {}
    def add(path, text):
        files[path] = text.strip() + '\n'
    files.update(API_MANAGER_FILES)
    add('lib/main.dart', """
import 'package:flutter/material.dart';
import 'app/app.dart';
import 'core/config/api_setup.dart';
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  initializeApi();
  runApp(const App());
}
""")
    add('lib/core/config/api_setup.dart', f"""
import '../../api/api.dart';
import 'app_config.dart';
void initializeApi() {{
  ApiManager.init(const ApiConfig(baseUrl: AppConfig.baseUrl),
    type: ApiClientType.{transport});
}}
""")
    extra = ''
    widget = "MaterialApp(title: " + dart_string(name) + ", theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true), home: const HomePage())"
    if manager == 'provider':
        extra = "import 'package:provider/provider.dart';\nimport '../features/counter/presentation/providers/counter_provider.dart';"
        widget = 'ChangeNotifierProvider(create: (_) => CounterProvider(), child: ' + widget + ')'
    elif manager == 'riverpod':
        extra = "import 'package:flutter_riverpod/flutter_riverpod.dart';"
        widget = 'ProviderScope(child: ' + widget + ')'
    elif manager in ('bloc', 'cubit'):
        cls = 'CounterBloc' if manager == 'bloc' else 'CounterCubit'
        extra = f"import 'package:flutter_bloc/flutter_bloc.dart';\nimport '../features/counter/presentation/{manager}/counter_{manager}.dart';"
        widget = f'BlocProvider(create: (_) => {cls}(), child: ' + widget + ')'
    elif manager == 'getx':
        extra = "import 'package:get/get.dart';\nimport '../features/counter/presentation/bindings/counter_binding.dart';"
        widget = widget.replace('MaterialApp(', 'GetMaterialApp(initialBinding: CounterBinding(), ')
    add('lib/app/app.dart', f"""
import 'package:flutter/material.dart';
import '../features/home/presentation/pages/home_page.dart';
{extra}
class App extends StatelessWidget {{
  const App({{super.key}});
  @override
  Widget build(BuildContext context) => {widget};
}}
""")
    add('lib/features/home/presentation/pages/home_page.dart', """
import 'package:flutter/material.dart';
import '../../../counter/presentation/pages/counter_page.dart';
import '../../../posts/presentation/pages/posts_page.dart';
class HomePage extends StatelessWidget {
  const HomePage({super.key});
  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 2,
    child: Scaffold(
      appBar: AppBar(title: const Text('Flutter Starter'), bottom: const TabBar(
        tabs: [Tab(text: 'Counter'), Tab(text: 'API demo')],
      )),
      body: const TabBarView(children: [CounterPage(), PostsPage()]),
    ),
  );
}
""")
    page_import = "import 'package:flutter/material.dart';\n"
    ui = "Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text('$count', key: const Key('counterValue'), style: Theme.of(context).textTheme.displayMedium), const SizedBox(height: 16), FilledButton(key: const Key('increment'), onPressed: increment, child: const Text('Increment'))])"
    if manager == 'provider':
        add('lib/features/counter/presentation/providers/counter_provider.dart', """
import 'package:flutter/foundation.dart';
class CounterProvider extends ChangeNotifier {
  int _count = 0;
  int get count => _count;
  void increment() { _count++; notifyListeners(); }
}
""")
        page_import += "import 'package:provider/provider.dart';\nimport '../providers/counter_provider.dart';\n"
        body = "final controller = context.watch<CounterProvider>(); final count = controller.count; final increment = controller.increment;"
    elif manager == 'riverpod':
        add('lib/features/counter/presentation/providers/counter_provider.dart', """
import 'package:flutter_riverpod/flutter_riverpod.dart';
final counterProvider = NotifierProvider<CounterNotifier, int>(CounterNotifier.new);
class CounterNotifier extends Notifier<int> {
  @override
  int build() => 0;
  void increment() => state++;
}
""")
        page_import += "import 'package:flutter_riverpod/flutter_riverpod.dart';\nimport '../providers/counter_provider.dart';\n"
        body = 'final count = ref.watch(counterProvider); final increment = ref.read(counterProvider.notifier).increment;'
    elif manager in ('bloc', 'cubit'):
        cls = 'CounterBloc' if manager == 'bloc' else 'CounterCubit'
        logic = "sealed class CounterEvent {}\nclass CounterIncremented extends CounterEvent {}\nclass CounterBloc extends Bloc<CounterEvent, int> { CounterBloc() : super(0) { on<CounterIncremented>((event, emit) => emit(state + 1)); } }" if manager == 'bloc' else 'class CounterCubit extends Cubit<int> { CounterCubit() : super(0); void increment() => emit(state + 1); }'
        add(f'lib/features/counter/presentation/{manager}/counter_{manager}.dart', "import 'package:flutter_bloc/flutter_bloc.dart';\n" + logic)
        page_import += f"import 'package:flutter_bloc/flutter_bloc.dart';\nimport '../{manager}/counter_{manager}.dart';\n"
        action = '() => controller.add(CounterIncremented())' if manager == 'bloc' else 'controller.increment'
        body = f'final controller = context.watch<{cls}>(); final count = controller.state; final increment = {action};'
    elif manager == 'getx':
        add('lib/features/counter/presentation/controllers/counter_controller.dart', "import 'package:get/get.dart';\nclass CounterController extends GetxController { final count = 0.obs; void increment() => count.value++; }")
        add('lib/features/counter/presentation/bindings/counter_binding.dart', "import 'package:get/get.dart';\nimport '../controllers/counter_controller.dart';\nclass CounterBinding extends Bindings { @override void dependencies() { Get.lazyPut<CounterController>(() => CounterController()); } }")
        page_import += "import 'package:get/get.dart';\nimport '../controllers/counter_controller.dart';\n"
        body = 'final controller = Get.find<CounterController>(); final increment = controller.increment;'
    else:
        body = ''
    if manager == 'setstate':
        page = f"""class CounterPage extends StatefulWidget {{
const CounterPage({{super.key}});
@override State<CounterPage> createState() => _CounterPageState();
}}
class _CounterPageState extends State<CounterPage> {{
int count = 0;
void increment() => setState(() => count++);
@override Widget build(BuildContext context) => Center(child: {ui});
}}"""
    else:
        base = 'ConsumerWidget' if manager == 'riverpod' else 'StatelessWidget'
        args = 'BuildContext context, WidgetRef ref' if manager == 'riverpod' else 'BuildContext context'
        child = f'Obx(() {{ final count = controller.count.value; return {ui}; }})' if manager == 'getx' else ui
        page = f'class CounterPage extends {base} {{ const CounterPage({{super.key}}); @override Widget build({args}) {{ {body} return Center(child: {child}); }} }}'
    add('lib/features/counter/presentation/pages/counter_page.dart', page_import + page)
    add('lib/core/config/app_config.dart', f"class AppConfig {{ static const baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: {dart_string(base_url)}); }}")
    add('lib/features/posts/data/models/post.dart', """
class Post {
  const Post({required this.id, required this.title, required this.body});
  final int id;
  final String title;
  final String body;
  factory Post.fromJson(Map<String, dynamic> json) => Post(
    id: (json['id'] as num).toInt(), title: json['title'] as String,
    body: json['body'] as String,
  );
}
""")
    add('lib/features/posts/data/repositories/post_repository.dart', """
import '../../../../api/api.dart';
import '../models/post.dart';
class PostRepository {
  const PostRepository(this.api);
  final ApiClient api;
  Future<List<Post>> fetchPosts() async {
    final data = await api.get('/posts');
    if (data is! List) throw ApiException(type: ApiErrorType.parse, message: 'Expected a JSON array of posts.');
    try {
      return data.map((item) => Post.fromJson(Map<String, dynamic>.from(item as Map))).toList();
    } catch (_) { throw ApiException(type: ApiErrorType.parse, message: 'The response does not match the Post model.'); }
  }
  Future<dynamic> createPost({required String title, required String body}) =>
    api.post('/posts', body: {'title': title, 'body': body, 'userId': 1});
}
""")
    add('lib/features/posts/presentation/pages/posts_page.dart', """
import 'package:flutter/material.dart';
import '../../../../api/api.dart';
import '../../data/models/post.dart';
import '../../data/repositories/post_repository.dart';
class PostsPage extends StatefulWidget {
  const PostsPage({super.key});
  @override State<PostsPage> createState() => _PostsPageState();
}
class _PostsPageState extends State<PostsPage> {
  late final ApiClient _api;
  Future<List<Post>>? _posts;
  @override void initState() { super.initState(); _api = ApiManager.client; }
  void _load() => setState(() { _posts = PostRepository(_api).fetchPosts(); });
  @override Widget build(BuildContext context) {
    if (_posts == null) return Center(child: FilledButton(onPressed: _load, child: const Text('Load posts')));
    return FutureBuilder<List<Post>>(future: _posts, builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
      if (snapshot.hasError) return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load posts.'),
        FilledButton(onPressed: _load, child: const Text('Retry')),
      ]));
      final posts = snapshot.data ?? [];
      if (posts.isEmpty) return Center(child: TextButton(onPressed: _load, child: const Text('No posts. Reload')));
      return RefreshIndicator(onRefresh: () async {
        final next = PostRepository(_api).fetchPosts();
        setState(() { _posts = next; });
        try { await next; } catch (_) { /* FutureBuilder displays the error. */ }
      }, child: ListView.builder(physics: const AlwaysScrollableScrollPhysics(),
        itemCount: posts.length, itemBuilder: (_, index) => ListTile(
          title: Text(posts[index].title), subtitle: Text(posts[index].body))));
    });
  }
}
""")
    add('test/widget_test.dart', f"""
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{name}/app/app.dart';
import 'package:{name}/core/config/api_setup.dart';
import 'package:{name}/api/api.dart';
void main() {{
  setUp(initializeApi);
  tearDown(() => ApiManager.client.close());
  testWidgets('selected state manager increments the counter', (tester) async {{
    await tester.pumpWidget(const App());
    expect(find.text('0'), findsOneWidget);
    await tester.tap(find.byKey(const Key('increment')));
    await tester.pump();
    expect(find.text('1'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  }});
}}
""")
    add('STARTER_README.md', f"""
# {name}
{description}

State management: **{manager}**. The Counter feature uses the selected manager;
the Posts API example uses Flutter FutureBuilder independently of that choice.
Only the chosen state package is installed. This generator supports six choices,
not every community state-management package.

## Run
```sh
flutter run
flutter run --dart-define=API_BASE_URL=https://your-api.example.com
flutter analyze
flutter test
```
The API demo makes no call until you press Load posts. Default API is
JSONPlaceholder; its write endpoints simulate success and do not persist data.
If you choose a different API, adapt Post and PostRepository to its schema.

## Structure
- lib/app: root app and state wiring
- lib/core/config: compile-time API base URL
- lib/api: your uploaded API manager, including both transports and its README
- lib/core/config/api_setup.dart: initializes ApiManager with the selected transport
- lib/features/counter/presentation: selected manager and example UI
- lib/features/posts/data: model and repository
- lib/features/posts/presentation: loading, error, retry, empty, list UI
- test/widget_test.dart: counter smoke test

## API examples
```dart
final api = ApiManager.client;
ApiManager.setAuthToken(yourStoredToken);
final posts = await api.get('/posts', query: {{'userId': 1}});
await api.post('/posts', body: {{'title': 'Hello', 'body': 'World', 'userId': 1}});
await api.put('/posts/1', body: {{'title': 'Updated'}});
await api.patch('/posts/1', body: {{'title': 'Changed'}});
await api.delete('/posts/1');
await api.post('/upload', body: ApiFormData.fromMap({{
  'name': 'Darshan',
  'file': ApiFile.fromBytes(selectedBytes, filename: 'photo.jpg'),
}}));
ApiManager.setAuthToken(null); // on logout
```
Import package:{name}/api/api.dart. See lib/api/README.md for the original documentation.
Transport selected at creation: **{transport}**. Change it in core/config/api_setup.dart.
The shared client is initialized once in main(), not owned or closed by individual screens.
Both dio and http dependencies are required because your manager imports both implementations.
`yourStoredToken` and `selectedBytes` are application-owned values; file picker,
login, refresh-token flow, and secure storage are not configured by this starter.
JSONPlaceholder does not provide /upload: use your actual upload endpoint.
Your original manager's debug logging is retained: it logs URLs and bodies and masks
the auth header. Set enableLogging: false in ApiConfig when handling sensitive payloads.
Use relative endpoints for your authenticated API; the original manager also accepts
absolute URLs and attaches its configured token to those requests.
Use HTTPS APIs. Native cleartext exceptions are deliberately not enabled.
For Flutter web, your API server must permit the app's origin via CORS.
Android INTERNET permission and macOS network-client entitlement are configured.
iOS builds need macOS/Xcode; each desktop target needs its host build toolchain.
Commit pubspec.lock for an app to retain the exact resolved dependency versions.
""")
    return files


def configure_network(root):
    manifest = root / 'android/app/src/main/AndroidManifest.xml'
    if manifest.exists():
        text = manifest.read_text(encoding='utf-8')
        if 'android.permission.INTERNET' not in text:
            text = text.replace('<application', '<uses-permission android:name="android.permission.INTERNET"/>\n    <application', 1)
            manifest.write_text(text, encoding='utf-8')
    for file in (root / 'macos/Runner').glob('*.entitlements'):
        text = file.read_text(encoding='utf-8')
        if 'com.apple.security.network.client' not in text:
            text = text.replace('</dict>', '<key>com.apple.security.network.client</key>\n<true/>\n</dict>')
            file.write_text(text, encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--name', help='Dart project name, e.g. my_app')
    parser.add_argument('--org', help='Organization, e.g. com.darshan')
    parser.add_argument('--description')
    parser.add_argument('--output', help='Parent directory (new project folder is created inside it)')
    parser.add_argument('--state', choices=MANAGERS)
    parser.add_argument('--platforms', help='Comma-separated targets')
    parser.add_argument('--base-url')
    parser.add_argument('--api-client', choices=('dio', 'http'), help='Backend used by your bundled API manager')
    parser.add_argument('--yes', action='store_true', help='Use defaults for missing answers; no prompts')
    parser.add_argument('--skip-checks', action='store_true', help='Skip analyze and widget tests')
    parser.add_argument('--scaffold-only', action='store_true', help='Generate Dart templates only, without Flutter; not a runnable platform project')
    args = parser.parse_args(argv)
    def value(current, label, default):
        return current if current is not None else (default if args.yes else ask(label, default))
    name = value(args.name, 'Project name', 'my_flutter_app')
    org = value(args.org, 'Organization / bundle prefix', 'com.example')
    description = value(args.description, 'Project description', 'Flutter application starter')
    parent = Path(value(args.output, 'Parent folder', '.')).expanduser().resolve()
    manager = args.state
    if manager is None and not args.yes:
        print('\nState management:')
        for index, choice in enumerate(MANAGERS, 1):
            print(f'  {index}. {choice}')
        choice = ask('Number or name', '1').lower()
        manager = MANAGERS[int(choice)-1] if choice.isdigit() and 1 <= int(choice) <= len(MANAGERS) else choice
    manager = manager or 'provider'
    platforms = value(args.platforms, 'Platforms (comma-separated)', 'android,ios,web').lower()
    platforms = ','.join(dict.fromkeys(x.strip() for x in platforms.split(',')))
    base_url = value(args.base_url, 'API base URL (HTTPS)', 'https://jsonplaceholder.typicode.com').rstrip('/')
    if not re.fullmatch(r'[a-z][a-z0-9_]*', name) or name in RESERVED or name in {'flutter', 'test', 'dart', 'provider', 'flutter_riverpod', 'flutter_bloc', 'get', 'dio', 'http', 'http_parser'}:
        parser.error('Name must be lower_snake_case, start with a letter and not be a reserved name.')
    if not re.fullmatch(r'[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+', org):
        parser.error('Use a lowercase reverse-domain organization, e.g. com.darshan.')
    if manager not in MANAGERS:
        parser.error('Choose a supported state-management option.')
    if not set(platforms.split(',')) <= PLATFORMS:
        parser.error('Platforms must be android,ios,web,windows,macos,linux.')
    url = urlsplit(base_url)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or any(c.isspace() for c in base_url):
        parser.error('Use an HTTPS API base URL without credentials, query or fragment.')
    transport = value(args.api_client, 'API client (dio/http)', 'dio').lower()
    if transport not in ('dio', 'http'):
        parser.error('API client must be dio or http.')
    root = parent / name
    if root.exists():
        parser.error(f'Refusing to overwrite existing path: {root}')
    flutter = shutil.which('flutter')
    if not args.scaffold_only and not flutter:
        parser.error('Flutter not found in PATH. Install Flutter, run flutter doctor, and retry.')
    print(f'\nProject: {root}\nState: {manager}\nPlatforms: {platforms}\nAPI: {base_url}\nAPI client: {transport}')
    if not args.yes and ask('Create project? y/n', 'y').lower() not in {'y', 'yes'}:
        print('Cancelled. No files changed.')
        return 0
    # Reserve a new directory; never merge with an existing project.
    parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()
    try:
        if not args.scaffold_only:
            run([flutter, 'create', '--no-pub', '--project-name', name, '--org', org,
                 '--description', description, '--platforms', platforms, str(root)])
        for relative, content in templates(name, manager, base_url, description, transport).items():
            file = root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding='utf-8')
        config = dict(name=name, organization=org, state=manager, platforms=platforms,
                      base_url=base_url, api_client=transport, scaffold_only=args.scaffold_only)
        (root / 'starter_config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
        if args.scaffold_only:
            print('Templates generated. No pubspec or native platform project was created.')
        else:
            configure_network(root)
            run([flutter, 'pub', 'add', 'dio:^5.9.0', 'http:^1.6.0', 'http_parser:^4.1.2', *PACKAGES[manager]], root)
            dart = shutil.which('dart')
            if not dart:
                raise RuntimeError('Dart not found in PATH; add Flutter bin to PATH.')
            run([dart, 'format', 'lib', 'test'], root)
            if not args.skip_checks:
                run([flutter, 'analyze'], root)
                run([flutter, 'test'], root)
            print(f'\nReady: {root}\nOpen this folder and run: flutter run')
        return 0
    except (subprocess.CalledProcessError, OSError, RuntimeError) as error:
        print(f'\nSetup did not finish: {error}\nPartial project preserved at {root}.\nFix the reported issue and continue there, or choose a new project name.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled. If creation had started, the partial folder is preserved.', file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(1)
