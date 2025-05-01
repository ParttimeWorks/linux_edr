import typer
from typing import Optional
from .app import LinuxEDRApp

app = typer.Typer()

@app.command()
def run(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    interval: Optional[int] = typer.Option(
        None, "--interval", "-i", help="Reporting interval in minutes"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for JSON reports"
    ),
    debug: Optional[bool] = typer.Option(
        None, "--debug", "-d", help="Enable debug logging"
    ),
):
    """
    Run Linux EDR monitoring.
    
    The application can be configured via a config.ini file or command line arguments.
    Command line arguments take precedence over configuration file settings.
    """
    LinuxEDRApp(
        config_path=config,
        interval=interval,
        output_file=output,
        debug=debug
    ).run()

@app.command()
def show_config(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
):
    """
    Show the current configuration values.
    
    This displays the effective configuration after loading from file
    and applying any environment variables.
    """
    from .config import Config
    import json
    
    cfg = Config(config)
    typer.echo(json.dumps(cfg.as_dict(), indent=2))

if __name__ == "__main__":
    app() 