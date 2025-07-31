from .McpServer import McpServer


def main():
    server = McpServer()
    server.run()


if __name__ == "__main__":
    main()