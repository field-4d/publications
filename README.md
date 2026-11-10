# Field 4D lab publications

Code accompanying publications from the Moshelion lab (Field 4D / PlantArray), Hebrew
University of Jerusalem. Each top-level folder holds the code for **one publication**, and
the folder name is the publication's title.

| Publication | Status | Maintainer |
|---|---|---|
| [Designed nutrient-gradient phenotyping enables predictive ionomics of tropical leafy greens](Designed%20nutrient-gradient%20phenotyping%20enables%20predictive%20ionomics%20of%20tropical%20leafy%20greens/) | submitted | @itamarshenhar |

Each folder is self-contained: its own `README.md` (how to run it and which script makes
which figure or table), dependencies, `LICENSE` and, ideally, `CITATION.cff`. Licences can
differ between folders. Datasets are not stored here unless a folder's README says so.

## Getting only one publication

```bash
git clone --filter=blob:none --sparse https://github.com/field-4d/publications.git
cd publications
git sparse-checkout set "Designed nutrient-gradient phenotyping enables predictive ionomics of tropical leafy greens"
```

## Adding or updating a publication

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: work on a branch, open a pull request
into `main`, and keep each pull request to your own publication's folder.
