import typer

app = typer.Typer()


@app.command()
def init():
    print("Keyhole developer environment initialized")


@app.command()
def runtime():
    print("Starting Keyhole test runtime")


if __name__ == "__main__":
    app()
