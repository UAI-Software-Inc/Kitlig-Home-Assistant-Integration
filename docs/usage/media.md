# Media and exports

Kitlig appears as a source in Home Assistant's media browser. Open **Media** in the sidebar and choose **Kitlig**.

## What you can browse

| Section | What is in it |
|---|---|
| Recent | The newest files of every kind. |
| Videos | Video files. |
| Images | Pictures. |
| Audio | Sound files. |
| Exports | Renders of your timelines, from the project's `exports` folder. |

With one Kitlig added, the sections appear right away. With several, you first choose the instance. Each is listed with its open project in brackets.

Pictures and videos show a thumbnail. Select a file to play or view it.

## What is left out

- Text files, zip files, 3D models and other kinds the media browser cannot show.
- Anything past the newest 600 files in a section.

## Playing on other devices

Files are passed through Home Assistant. Your browser or phone only talks to Home Assistant, and Home Assistant fetches the file from Kitlig. Two things follow from that:

- Media works wherever your Home Assistant works, including away from home.
- Kitlig's sign-in never reaches the browser.

You can also send a file to a media player, such as a TV, from the media browser. The player needs to be able to reach Home Assistant and to play the file's format.

Video can seek. Large files start playing before they have fully loaded.

## The latest result on a dashboard

The **Latest media** image entity always holds the newest picture or poster frame. Add a picture entity card to show it:

```yaml
type: picture-entity
entity: image.studio_latest_media
show_name: false
show_state: false
```

## Reviews and exports

The **Exports** section lists the rendered files. For review status, use the **Open review comments** sensor. Its `sequences` attribute lists each sequence with its open comment count, its latest export, and whether the timeline has changed since that export.

Reading and writing the comments themselves happens in Kitlig or in the Kitlig phone app.
