# Original developer-published cartridges. These are fetchurl inputs, not a
# Korri game catalogue. CREDITS.md maps the original names to the 24 selections.
{ pkgs }:
[
  (pkgs.fetchurl {
    name = "celeste_classic_2-5.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/ce/celeste_classic_2-5.p8.png";
    hash = "sha256-FbHyY5yN0jfdsRdrHZ8xG7lgCCt4BmjhTA8dD9j42W0=";
  })
  (pkgs.fetchurl {
    name = "combopool-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/co/combopool-0.p8.png";
    hash = "sha256-h/MK25k2ZoQjvPQvygRwqbOxvH8iaOy53fC2F6fAXts=";
  })
  (pkgs.fetchurl {
    name = "mot_taxi-7.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/mo/mot_taxi-7.p8.png";
    hash = "sha256-9C/9DPuHzCTZ6yb5K9RVPUaxsr71xu4gHluWZbI8rI8=";
  })
  (pkgs.fetchurl {
    name = "birdswithguns-5.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/bi/birdswithguns-5.p8.png";
    hash = "sha256-VSFXrBmHYbCERGupM1q0S5mxoJ2HB2XduSFf3eHYAvU=";
  })
  (pkgs.fetchurl {
    name = "demon_castle-1.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/de/demon_castle-1.p8.png";
    hash = "sha256-n7S9JrjaY21dKJ+MYnK6/plVfK4iyCFFlQxUctfiF8w=";
  })
  (pkgs.fetchurl {
    name = "littlenecromancer-4.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/li/littlenecromancer-4.p8.png";
    hash = "sha256-5tBKLS5L4k+2q4CCputat4mTD5j+waUwe4DE8wsZtO8=";
  })
  (pkgs.fetchurl {
    name = "ufo-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/uf/ufo-0.p8.png";
    hash = "sha256-RzZNGYL+2We0yGehBP2creE2Bs/lBZiVJZeRhrsoues=";
  })
  (pkgs.fetchurl {
    name = "d16solais-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/d1/d16solais-0.p8.png";
    hash = "sha256-4Q/8HzvGkmfMixniO6H8o8K6zpZj/Lu0u7RyLdmGUAE=";
  })
  (pkgs.fetchurl {
    name = "pigments-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/pi/pigments-0.p8.png";
    hash = "sha256-YCLz42iE4C6oUfNWY6br7vC95R0hRqZewdVB/I0bn1Y=";
  })
  (pkgs.fetchurl {
    name = "highstakes-2.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/hi/highstakes-2.p8.png";
    hash = "sha256-pc/4diNv3EoiVoS0P1rPksuOnga8Et6BncrFISM8OrY=";
  })
  # The author's v1.07 offline pair uses local load() targets. The BBS title
  # cart downloads its companion, so it is not the offline distribution.
  (pkgs.fetchurl {
    name = "intoruins.p8.png";
    url = "https://raw.githubusercontent.com/Woflox/intoruins/25fd2e196f9cf970de6ee7aa2ba211bcbb94bfe3/carts/offline/intoruins.p8.png";
    hash = "sha256-VS0pu3lcLCjMx0PVm+K0fwNhoT13jPYIogXN8EIpxis=";
  })
  (pkgs.fetchurl {
    name = "intoruins_main.p8.png";
    url = "https://raw.githubusercontent.com/Woflox/intoruins/25fd2e196f9cf970de6ee7aa2ba211bcbb94bfe3/carts/offline/intoruins_main.p8.png";
    hash = "sha256-2jopDEITivi5XiNuM66nXhkCTDi1g/S4+zTAFr06wXE=";
  })
  (pkgs.fetchurl {
    name = "air_delivery_1-3.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/ai/air_delivery_1-3.p8.png";
    hash = "sha256-aDra8ZIzWVB3qQRGU0PCvE447r8X5LV6ER8AH/e3oKM=";
  })
  (pkgs.fetchurl {
    name = "marble_merger-5.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/ma/marble_merger-5.p8.png";
    hash = "sha256-nZhZLoiafopu+qwlNPCfcLN3DZa1IZEcNq3+/jRvDAc=";
  })
  (pkgs.fetchurl {
    name = "proserpinasquest-3.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/pr/proserpinasquest-3.p8.png";
    hash = "sha256-Jk5Ca0QJqoR7GQ7KkPRVCL4C6NeZKwQkkpSxg4jqYV8=";
  })
  (pkgs.fetchurl {
    name = "cherrybomb-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/ch/cherrybomb-0.p8.png";
    hash = "sha256-5rIjzI2R/e2DYFREz572g2boiph3E+XGu79CYBY+UeM=";
  })
  (pkgs.fetchurl {
    name = "42930.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/4/42930.p8.png";
    hash = "sha256-aHZJ202AvvsCliUSwzVAiDsxsHRWMSqtpr89/EJNf4A=";
  })
  (pkgs.fetchurl {
    name = "51894.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/5/51894.p8.png";
    hash = "sha256-ViO0aNcJm1MVE3h+9waQo3stKhfhuRUQhryI4aj2Sx0=";
  })
  (pkgs.fetchurl {
    name = "56576.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/5/56576.p8.png";
    hash = "sha256-ujJQrQ8+c4RNcAMTnsD0bv5wjUdkusfVUHX4Ud2/4d4=";
  })
  (pkgs.fetchurl {
    name = "37216.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/3/37216.p8.png";
    hash = "sha256-B8EVX2OgoT5jAO+a74omsN9lDxXrJKntc7toOU8HnAo=";
  })
  (pkgs.fetchurl {
    name = "23208.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/2/23208.p8.png";
    hash = "sha256-MQpXwnsMKkmmz+aPCp/d9evLSzW+bzhcFpXaWzK+/80=";
  })
  (pkgs.fetchurl {
    name = "16305.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/1/16305.p8.png";
    hash = "sha256-qIIh+9OQyBnZHbhDhXUyUALNToXeQnRpAQiViqCqPmU=";
  })
  (pkgs.fetchurl {
    name = "48406.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/4/48406.p8.png";
    hash = "sha256-nix3WYJq9VlpfgxpozHIoU2y3dWxEIvJHqn74VcHBtE=";
  })
  (pkgs.fetchurl {
    name = "vitreous-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/vi/vitreous-0.p8.png";
    hash = "sha256-ys/Bm9iqpufxmuo25cjHJuQ6iV5FqKIIkS7LGGmYYv4=";
  })
  (pkgs.fetchurl {
    name = "dungeonsolitaire-0.p8.png";
    url = "https://www.lexaloffle.com/bbs/cposts/du/dungeonsolitaire-0.p8.png";
    hash = "sha256-B6s4gXxRvd9OzdngQYo/fVqm4/DzG6KKWmdgXeco+/M=";
  })
]
