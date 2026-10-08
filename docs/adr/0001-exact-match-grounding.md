# Grounded means exact match only

A value counts as grounded only when LangExtract reports an exact alignment and the filing text at that span equals the extracted text. Fuzzy and lesser alignments count as not grounded, even when the value itself is correct. We chose this because looser alignments were seen pointing at the wrong tranche (the AAPL 2028 coupon `4.000%` was anchored to `"4."` inside the 2030 section), and the whole point of the tool is that a cell's source link can be trusted. The cost is a lower grounding figure: the first strict run dropped it from a claimed 100% to 57.1%.
