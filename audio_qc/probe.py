            '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '2',
            '-i', stream_url,
            '-t', '20', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(AUDIO_FILE),
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
            diagnostic = scrub(p.stderr, sensitive_urls)
            LOG_FILE.write_text(diagnostic, encoding='utf-8')
            result['ffmpeg_exit_code'] = p.returncode
            if p.returncode != 0:
                raise RuntimeError('FFmpeg thất bại; xem ffmpeg_diagnostic.log')
        except subprocess.TimeoutExpired as e:
            diagnostic = scrub(e.stderr.decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else e.stderr, sensitive_urls)
            LOG_FILE.write_text('FFMPEG_TIMEOUT_65S\n' + diagnostic, encoding='utf-8')
            raise RuntimeError('FFmpeg timeout sau 65 giây; xem ffmpeg_diagnostic.log') from None
        result['stage'] = 'validate_audio'
        if not AUDIO_FILE.exists() or AUDIO_FILE.stat().st_size < 32000:
            raise RuntimeError('Audio không tồn tại hoặc quá nhỏ')
        duration = probe_duration(AUDIO_FILE)
        result['duration_seconds'] = round(duration, 2)
        result['bytes'] = AUDIO_FILE.stat().st_size
        if duration < 10:
            raise RuntimeError(f'Audio chỉ dài {duration:.1f}s; cần ít nhất 10s để kiểm tra')
        result['audio_file'] = str(AUDIO_FILE)
        result['status'] = 'CAPTURED_UNVERIFIED'
        result['stage'] = 'complete'
    except Exception as e:
        result['error'] = scrub(str(e), sensitive_urls)
    finally:
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'CAPTURED_UNVERIFIED' else 1


if __name__ == '__main__':
    sys.exit(main())
