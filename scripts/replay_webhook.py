def main() -> None:
    raise SystemExit("HTTP webhook 回放已弃用：当前项目使用 WebSocket 长连接接收事件。请改用: python scripts/local_e2e.py")


if __name__ == "__main__":
    main()
