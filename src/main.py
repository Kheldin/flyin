from parsing.parsing import parse_file

def main():
    try:
        parse_file()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    # try:
    #     main()
    # except Exception as e:
    #     print(e)
    main()