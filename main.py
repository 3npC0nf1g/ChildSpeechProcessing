from classify_cha import classify_cha_files_in_directory

results = classify_cha_files_in_directory("data/2")

for t, files in results.items():
    print(f"\nType {t}: {len(files)} files")
    for f in files[:3]:
        print("  ", f)