# Parses tsv dump of registration nettskjema
# And gives statistics
# Use: sh obiwow.sh data-####-20##-##-##-####-utf.txt
infile=$1
echo how many people signed up
cat $infile | awk -F '\t' '{print $6}' | sort | uniq -c | wc -l
echo
echo how many times did someone sign up
cat $infile | awk -F '\t' '{print $6}' | sort | uniq -c | sort -nr | head
echo
echo how many signed up per workshop:
cat $infile | awk -F '\t' '{print $4}' | sort | uniq -c | sort -nr | awk '{print $2"\t"$1}'
