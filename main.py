from parser import parse_task


def main():
    print("=== Task Parser NLP ===")
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
        except Exception as e:
            print(f"  Error parsing task: {e}")
            continue

        print("\nParsed Output:")
        for key, value in result.items():
            if value is not None:
                print(f"  {key:>14}: {value}")
        print("-" * 40)


if __name__ == "__main__":
    main()