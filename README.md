Tools to process information useful for DJs as Onya knowledge graphs.

https://github.com/uogbuji/onya.dj/


# Docker Notes

1. Install docker
2. `JUPYTER_TOKEN="SeratoDBNB" SDB="$HOME/Music/_Serato_/database V2" docker compose up -d`
  * Replace the SDB string with wherever your Serato database is located. Above should work with Macs not using any special setup
  * Replace `SeratoDBNB` with a token string of your choosing
3. In your bowser open http://localhost:8888/notebooks/notebook/notebook/serato-explore.ipynb and at in the token input enter whatever token you chose
  * Select the top portion of the code and click "run", then select the second portion and click "run". A text field should pop up below it preset with "SWV". Now you should be able to type into the text field and get DB search results
4. When you're done, bring down the container using `SDB="$HOME/Music/_Serato_/database V2" docker compose down`
  * You might also have to do `docker rm onya-dj-notebook` in order to avoid conflicts on re-launch. Investigating…


## Notes

* If you don't properly set up the $SDB variable you'll get an error such as "error decoding 'Volumes[0]': invalid spec: :/sdb:ro: empty section between colons"


