Text reading preferences: "UTF-8"
Text writing preferences: "UTF-8"
input_dir$ = "/Users/liutong/Desktop/mfa_align/audio/"
strings = Create Strings as file list: "wav", input_dir$ + "*.wav"
num_files = Get number of strings
for ifile to num_files
    selectObject: strings
    filename$ = Get string: ifile
    Read Strings from raw text file: input_dir$ + filename$ - ".wav" + ".txt"
    txt = selected("Strings", 1)
    content$ = Get string: 1
    Read from file: input_dir$ + filename$
    sound = selected("Sound", 1)
    To TextGrid: "utt", ""
    textgrid = selected("TextGrid", 1)
    Set interval text: 1, 1, content$
    Save as text file: input_dir$ + filename$ - ".wav" + ".TextGrid"
    select all
    minusObject: strings
    Remove
endfor
selectObject: strings
Remove