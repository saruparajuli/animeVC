from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_character_page(character_name):
   
    char_resp = requests.get("https://myanimelist.net/character/{0}".format(character_name), headers=HEADERS)
    char_soup = BeautifulSoup(char_resp.text, "html.parser")
    
    voice_actors = {"japanese": [], "english": []}
    
    # MAL character pages include a "Voice Actors" section.
    # (The actual selector may vary. Here we assume a div with class "anime_voice_seiyuu".)
    for row in char_soup.find_all("tr"):
            a_tag = row.find_all("a", href=lambda href: href and "/people/" in href)
            img = row.find('img').get('data-src').split('?s')[0].replace('/r/84x124/images/', '/images/')
            if a_tag:
                a_tag = a_tag[1]
                actor_name = a_tag.text.strip()
                if not actor_name:
                    continue
                actor_url = a_tag["href"]
                # Assume the language is in one of the <td> cells (typically the last one)
                cells = row.find_all("td")
                if cells:
                    language = cells[-1].text.strip()
                    if "Japanese" in language:
                        voice_actors["japanese"].append({
                            "name": actor_name,
                            "url": actor_url,
                            "image": img
                        })
                    elif "English" in language:
                        voice_actors["english"].append({
                            "name": actor_name,
                            "url": actor_url,
                            "image": img
                        })
    return voice_actors

def scrape_voice_actor_filmography(actor_url):
    """
    Given a MAL voice actor (people) page URL, scrape a list of roles.
    (Again, actual selectors may vary – here we assume the roles are listed in a div with class "voice_acting_roles".)
    """
    resp = requests.get(actor_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    filmography = []
    for row in soup.find_all("tr", class_='js-people-character'):
        img = row.find_all('img')[1].get('data-src').split('?s')[0].replace('/r/84x124/images/', '/images/')
        title = row.find_all('a', class_='js-people-title')[0].text.strip()
        for a in row.find_all("a", href=lambda href: href and "/character/" in href):
            role = a.text.strip()
            if role and role not in filmography:
                filmography.append((role, title, img))
    return filmography

def build_mind_map(voice_actors):
    """
    Build a nested mind map structure where the root node is "Voice Actors"
    and each voice actor (with language category) is a child with their filmography as further children.
    """
    mind_map = {"name": "Voice Actors", "children": []}
    for category in ["japanese", "english"]:
        for actor in voice_actors.get(category, []):
            filmography = scrape_voice_actor_filmography(actor["url"])
            actor_node = {
                "name": actor["name"],
                "img": actor["image"],
                "category": category,
                "children": [{"name": role[0], "title":role[1], "img":role[2]} for role in filmography]
            }
            mind_map["children"].append(actor_node)
    return mind_map

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    character = request.form.get("character")
    if not character:
        return "Please enter a character name", 400
    # Scrape MAL character page for voice actor data
    """
    Search MyAnimeList for a character and scrape its page for voice actor data.
    Returns a dictionary with lists for "japanese" and "english" voice actors.
    """
    # Search URL – MAL character search page:
    search_url = f"https://myanimelist.net/character.php?q={character}"
    search_resp = requests.get(search_url, headers=HEADERS)
    search_soup = BeautifulSoup(search_resp.text, "html.parser")
    
    # Find first character link – MAL character links contain '/character/' in href.
    data = []
    dataImg = []
    links = search_soup.find_all("a", href=lambda href: href and "/character/" in href)
    for i in range(1, len(links)-1, 2) :
        try:
            print(links[i-1])
            data.append((links[i-1]['href'].split('/character/')[1].split('/')[0], links[i].text.strip(), links[i-1].find('img')['data-src'].replace('/r/42x62/images/', '/images/') ))
        except:
            continue
    if links == []:
        return {"japanese": [], "english": []}
    else:
        return render_template('index.html', links=data)
    
    
    character_url = first_link["href"]
    return render_template('index.html', )
    voice_actors = scrape_character_page(character)
    # Build the mind map structure
    mind_map = build_mind_map(voice_actors)
    return render_template("mindmap.html", mind_map_data=mind_map, character=character)

@app.route("/mindmap", methods=["GET"])
def build():
    charID = request.args.get('id')
    charName = request.args.get('name')
    voice_actors = scrape_character_page(charID)
    mind_map = build_mind_map(voice_actors)
    return render_template("mindmap.html", mind_map_data=mind_map, character=charName)

if __name__ == "__main__":
    app.run(debug=True)
