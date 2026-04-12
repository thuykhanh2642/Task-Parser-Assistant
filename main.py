from parser import parse_task


def main() -> None:
    print("=== Task Parser Assistant ===")
    print("Enter a task sentence. Type 'q' to quit.\n")

    while True:
        try:
            text = input("Enter task: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Task Parser.")
            break

        if not text or text.lower() == "q":
            print("Exiting Task Parser.")
            break

        try:
            result = parse_task(text)
        except Exception as exc:
            print(f"  Error parsing task: {exc}")
            continue

        print("\nParsed Output:")
        for key, value in result.model_dump(mode="json").items():
            print(f"  {key:>14}: {value}")
        print("-" * 40)


if __name__ == "__main__":
    main()
