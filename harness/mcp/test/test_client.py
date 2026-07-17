import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():

    async with streamable_http_client(
        "http://127.0.0.1:8000/mcp"
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            # ============================
            # Source Search V2 Test
            # ============================

            search_result = await session.call_tool(
                "source_search",
                {
                    "keyword": "sp_object",
                    "max_results": 10,
                    "case_sensitive": False,
                },
            )

            print("\n=== SOURCE SEARCH V2 ===")

            if search_result.structuredContent:
                for item in search_result.structuredContent["result"]:
                    print(
                        f"{item['path']}:{item['line_no']} "
                        f"[{item['file_type']}] "
                        f"{item['line_text']}"
                    )

            # ============================
            # Source Read Test
            # ============================

            read_result = await session.call_tool(
                "source_read",
                {
                    "path": "engine/runtime/object_runtime_engine.py",
                    "start_line": 550,
                    "max_lines": 30,
                },
            )

            print("\n=== SOURCE READ ===")
            print(f"isError = {read_result.isError}")

            if read_result.structuredContent:
                read_data = read_result.structuredContent["result"]

                print(
                    f"{read_data['path']} "
                    f"{read_data['start_line']}-"
                    f"{read_data['end_line']} "
                    f"/ total {read_data['total_lines']}"
                )

                for item in read_data["content"]:
                    print(
                        f"{item['line_no']:5} | "
                        f"{item['line_text']}"
                    )
            else:
                print("structuredContent 없음")

                for content_item in read_result.content:
                    print(content_item.text)

            # ------------------------------------
            # Table Schema   ← 여기 추가
            # ------------------------------------

            table_result = await session.call_tool(
                "table_schema",
                {
                    "table_name": "sp_object",
                },
            )

            print("\n=== TABLE SCHEMA ===")

            print(f"isError = {table_result.isError}")

            if table_result.structuredContent:

                print(table_result.structuredContent)

            else:

                for item in table_result.content:
                    print(item.text)
            
            #--------------------------------------------
            # TABLE DATA
            #--------------------------------------------
            table_data_result = await session.call_tool(
                "table_data",
                {
                    "table_name": "sp_object",
                },
            )

            print("\n=== TABLE DATA ===")
            print(f"isError = {table_data_result.isError}")

            if table_data_result.structuredContent:
                print(table_data_result.structuredContent)
            else:
                for item in table_data_result.content:
                    print(item.text)

            # ============================
            # Git Status Test
            # ============================

            git_result = await session.call_tool(
                "git_status",
                {},
            )

            print("\n=== GIT STATUS ===")

            print(f"isError = {git_result.isError}")

            if git_result.structuredContent:

                print(git_result.structuredContent)

            else:

                for item in git_result.content:

                    print(item.text)

            # ============================
            # Git Diff Test
            # ============================

            git_diff_result = await session.call_tool(
                "git_diff",
                {
                    "path": "harness/mcp/sps_harness_server.py",
                },
            )

            print("\n=== GIT DIFF ===")
            print(f"isError = {git_diff_result.isError}")

            if git_diff_result.structuredContent:
                print(git_diff_result.structuredContent)
            else:
                for item in git_diff_result.content:
                    print(item.text)

            # ============================
            # Tool List Test
            # ============================

            tools = await session.list_tools()

            print("\n=== TOOLS ===")

            for tool in tools.tools:
                print(f"- {tool.name}")


asyncio.run(main())