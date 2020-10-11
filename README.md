
# Medical Concept Extraction
A method for language-agnostic human-in-the-loop medical concept extraction from highly unstructured electronic health records.

## Usage
Works best in an interactive session.

**Loading records**  
Load your text files into record objects using the helper classes in `data_utils`:

    records = Records()
    for i, text in enumerate(raw_record_strings):
        records.append(Record(i, text))
        
    # optionally save the tokenized records as a pickle file
    records.save()  # load with Records.load

**Initial curation**  
Add your bootstrap lexicon to the data folder as a newline separated `lexicon.txt` file.
`AnnotationGUI` starts a GUI where you can annotate tokens with right mouse button.
You can use `extraction.extract_all` to pre-annotate the records using your bootstrap lexicon.

    lexicon = build_lexicon()  
    
    extract_all(records, lexicon) # pre-annotate tokens that are contained in the lexicon
    gui = AnnotationGUI(records)  
    tags = gui.annotated
    fps = get_false_positives(records, lexicon)  

Inspect the false positives returned by `curation.get_false_positives`. 
Remove or add annotation mistakes, or mark lexicon entries as ambiguous, using the methods in `curation.py`. 

Example false positive returned: 
`(('none', 'administered'), 40110, (14, 4), ('medication', ':', 'none', 'administered', '.'))`
Remove with:
`remove_tag(tags, fps[0][1], fps[0][2])`
Or mark as ambiguous:
`mark_ambiguous(lexicon, fps[0][0])`

**Review candidates**  

    cdf = CandidateFinder(records, lexicon)  
    cdf.extend_fuzzy()  # find fuzzy matches
    cdf.process_contexts()  # find lexicon match contexts
    cdf.get_candidates()  # sets cdf.candidates to a list of candidates ordered by their occurrence count
    cdf.start_review()  # opens the review GUI
    cdf.save_all()  # saves the lexicon, rejected entries, and partial match statistics


Then later load with:

    cdf = CandidateFinder(records)
    cdf.load_all()

**Exctract matches**  
Annotate using `extraction.extract_all` with the saved partial match statistics.

    # tags are saved in Record.tags
    extract_all(records, lexicon, cdf.pos_counter, cdf.pos_counter_m)

