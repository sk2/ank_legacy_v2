import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")


def test_plot():
    inet = AutoNetkit.internet.Internet("multias") 
    inet.compile()
    inet.plot()
    assert(os.path.exists(os.path.join(config.plot_dir, "summary.html")))
    js_plot_files = ["arbor.js", "dns_auth.js", "dns.js", "ebgp.js", "ibgp.js", "igp.js", "ip.js", "main.js"]
    for js_file in js_plot_files:
        assert(os.path.exists(os.path.join(config.plot_dir, "jsplot", js_file)))

    inet.plot(matplotlib=True)

