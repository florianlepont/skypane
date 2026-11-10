"""The synthetic firmware image builder's output is pinned byte for byte.

Each entry maps 'size|signed|corrupt|modulus|version' to (length, sha256 of
the image). The digests were recorded from the builder before it was optimised, so
any change to the produced bytes (a different padding length, checksum,
digest, signature sector or truncation) fails here.
"""
import hashlib

import pytest

import skypane_fw_image as fw

PINNED = {
    'None|True|None|default|fw-v1.2.3': (8192, 'c50935a356433eaf99e4d0132690ecbe66c22d3d710afab545da330cc3164bfc'),
    'None|True|None|default|fw-v9.0.0': (8192, '3355b65491d42ee2fe085cc233453faa5b9a2c49ea71bbb790e1f30bcbdb4276'),
    'None|True|None|other|fw-v1.2.3': (8192, 'cbd83c5f6c5070927aaaa99a77d0fa507bce8ca7ae21789e7610a5ea9e32f531'),
    'None|True|None|other|fw-v9.0.0': (8192, 'c0d0c22b26d3b6ec00d92d4f1122a96af1c92a5bb852f4b272fd5d4cce0770b2'),
    'None|True|digest|default|fw-v1.2.3': (8192, 'b0141c2b89f46c4d99bb2804560e9481678d4c2d149c3fcdc5c45047815a8267'),
    'None|True|digest|default|fw-v9.0.0': (8192, '9d1804ac996cbeb1b0a036f18152f4f201818734dfba671e70c15fde2b41a58d'),
    'None|True|digest|other|fw-v1.2.3': (8192, '6ccb199767ba61798d86df9adc34762408c05f38cf6a1143d7fa4d8071e1cecb'),
    'None|True|digest|other|fw-v9.0.0': (8192, 'f14589655314cfcfb146cee90b3433adb4c18b8134f0d0fd502140ac05d74d66'),
    'None|True|signature_digest|default|fw-v1.2.3': (8192, '4cebef128bdd2fc90145bdb206d2a9a0e0b2320975520e337c99e666220ec6d9'),
    'None|True|signature_digest|default|fw-v9.0.0': (8192, 'dbb97004b15189022d06cdc9f06d6205335fd8cdeacdc72315e1b7f53d9cb38d'),
    'None|True|signature_digest|other|fw-v1.2.3': (8192, 'f1032abe608787772832f9a9e94113d186752cce6af23114f6ddd6a1c15df631'),
    'None|True|signature_digest|other|fw-v9.0.0': (8192, 'ef16237169452ff7f7cf77096528f33cc59cdc92be703b447f6771b80234f601'),
    'None|True|truncate|default|fw-v1.2.3': (8092, 'b6d0c82c5e8cd6669702fd448fa12383847db1e643968f6df79f048b89f5a1e4'),
    'None|True|truncate|default|fw-v9.0.0': (8092, 'ff3ac7407dcba07789ea4313151a1293f9b3b02325f0ff1ce0ce2810da035cb6'),
    'None|True|truncate|other|fw-v1.2.3': (8092, 'd81388b511a776a1f623b52b60d984040d05690b91580e637c272d0c2e85a370'),
    'None|True|truncate|other|fw-v9.0.0': (8092, '2470d98d4da861b628fb6943aea6c8c72fb2c87cb28110504b23572602b124cb'),
    'None|True|unterminated_version|default|fw-v1.2.3': (8192, '1f367473317b9282eb1837dc9186bfc89bda9f71795c5c20aab49eabe0a131e6'),
    'None|True|unterminated_version|default|fw-v9.0.0': (8192, '1f367473317b9282eb1837dc9186bfc89bda9f71795c5c20aab49eabe0a131e6'),
    'None|True|unterminated_version|other|fw-v1.2.3': (8192, '267e18929d86f6306029d472f91fb3ca03fc319d307035f361c3c9aa428f852a'),
    'None|True|unterminated_version|other|fw-v9.0.0': (8192, '267e18929d86f6306029d472f91fb3ca03fc319d307035f361c3c9aa428f852a'),
    'None|True|magic|default|fw-v1.2.3': (8192, '8a2ade79d39eaec445be597fedbc887dd259367f757e138d492eba9b51f0d0a6'),
    'None|True|magic|default|fw-v9.0.0': (8192, '19af0b6e3dcdae1c1d8e33e37b67b637f255cacb89db90d6f45561a0e2ac8790'),
    'None|True|magic|other|fw-v1.2.3': (8192, '655c58a75dfede748b13e5f50e727658a8ab3567f467e5361986f753512354fe'),
    'None|True|magic|other|fw-v9.0.0': (8192, '6448e779f2da517d4f465aa20cdb2f933f47ba8f792c86c2d088a1e43cf6fc5e'),
    'None|True|descriptor_magic|default|fw-v1.2.3': (8192, 'e7b25564f90407b7acafc6f0bcdccbe0455864f28a7aa63f1d6cf54d16924cd7'),
    'None|True|descriptor_magic|default|fw-v9.0.0': (8192, '8bbc76a51f4303d3bbf88941436655a26c57a946c6a0b220dea99a974f035b80'),
    'None|True|descriptor_magic|other|fw-v1.2.3': (8192, '286b1b5b5b050fb166db00f1df0a137bae69a61af176ae9cc16b322e73e19c1a'),
    'None|True|descriptor_magic|other|fw-v9.0.0': (8192, '9a835a694a35e0ff2565a274c67526e56d4fe85a1fac9aec2d9409e30c12b385'),
    'None|False|None|default|fw-v1.2.3': (336, '34ef6e2d91f2abded49a15249a28cd15ffe267f1613e3e00b394afa260a29e3d'),
    'None|False|None|default|fw-v9.0.0': (336, 'c205b666bba83f7fb3f3f594bdbff5e4defdc670ed678ea4601ea8264ddcc907'),
    'None|False|None|other|fw-v1.2.3': (336, '34ef6e2d91f2abded49a15249a28cd15ffe267f1613e3e00b394afa260a29e3d'),
    'None|False|None|other|fw-v9.0.0': (336, 'c205b666bba83f7fb3f3f594bdbff5e4defdc670ed678ea4601ea8264ddcc907'),
    'None|False|digest|default|fw-v1.2.3': (336, '36804183868165b136ac709b11435549ce84ffbb0d4176a517f3fa6330cbe105'),
    'None|False|digest|default|fw-v9.0.0': (336, 'fc9fe8c57fc4e0f9a9eaab0d178d157ee4c60a70e5cc441a7219fe520bfb1032'),
    'None|False|digest|other|fw-v1.2.3': (336, '36804183868165b136ac709b11435549ce84ffbb0d4176a517f3fa6330cbe105'),
    'None|False|digest|other|fw-v9.0.0': (336, 'fc9fe8c57fc4e0f9a9eaab0d178d157ee4c60a70e5cc441a7219fe520bfb1032'),
    'None|False|signature_digest|default|fw-v1.2.3': (336, '34ef6e2d91f2abded49a15249a28cd15ffe267f1613e3e00b394afa260a29e3d'),
    'None|False|signature_digest|default|fw-v9.0.0': (336, 'c205b666bba83f7fb3f3f594bdbff5e4defdc670ed678ea4601ea8264ddcc907'),
    'None|False|signature_digest|other|fw-v1.2.3': (336, '34ef6e2d91f2abded49a15249a28cd15ffe267f1613e3e00b394afa260a29e3d'),
    'None|False|signature_digest|other|fw-v9.0.0': (336, 'c205b666bba83f7fb3f3f594bdbff5e4defdc670ed678ea4601ea8264ddcc907'),
    'None|False|truncate|default|fw-v1.2.3': (236, '27a8e695d366c00b55063c3a3ebdbed5c39290df987ca5d42799a80c6d0e4f46'),
    'None|False|truncate|default|fw-v9.0.0': (236, '3673562e3b033b554029604ccdd3b332eac5c91cabfa15eb21d1f2cdb6bd9228'),
    'None|False|truncate|other|fw-v1.2.3': (236, '27a8e695d366c00b55063c3a3ebdbed5c39290df987ca5d42799a80c6d0e4f46'),
    'None|False|truncate|other|fw-v9.0.0': (236, '3673562e3b033b554029604ccdd3b332eac5c91cabfa15eb21d1f2cdb6bd9228'),
    'None|False|unterminated_version|default|fw-v1.2.3': (336, '89615c0baaf82e8a0faf51af5f0244f81fbb7501fd39122923b21d34533d0fe7'),
    'None|False|unterminated_version|default|fw-v9.0.0': (336, '89615c0baaf82e8a0faf51af5f0244f81fbb7501fd39122923b21d34533d0fe7'),
    'None|False|unterminated_version|other|fw-v1.2.3': (336, '89615c0baaf82e8a0faf51af5f0244f81fbb7501fd39122923b21d34533d0fe7'),
    'None|False|unterminated_version|other|fw-v9.0.0': (336, '89615c0baaf82e8a0faf51af5f0244f81fbb7501fd39122923b21d34533d0fe7'),
    'None|False|magic|default|fw-v1.2.3': (336, '65955fd9d04b4bb21454bc4eb6760938be3869974d4c1a767654e0cb49321a5b'),
    'None|False|magic|default|fw-v9.0.0': (336, 'ec913286658909ca90e41530eac8afe67f88cdfa3f4223c2fb9f2762ccaa17c1'),
    'None|False|magic|other|fw-v1.2.3': (336, '65955fd9d04b4bb21454bc4eb6760938be3869974d4c1a767654e0cb49321a5b'),
    'None|False|magic|other|fw-v9.0.0': (336, 'ec913286658909ca90e41530eac8afe67f88cdfa3f4223c2fb9f2762ccaa17c1'),
    'None|False|descriptor_magic|default|fw-v1.2.3': (336, 'ed587fc9cf4b95a9b7197f757c7db0b25dee5abeff354e2cef464ca2c18cf45f'),
    'None|False|descriptor_magic|default|fw-v9.0.0': (336, 'ac65f07c5daefbeb5a99f016f5eeded6a8984f0b3a4b3638627a3a4403d0931b'),
    'None|False|descriptor_magic|other|fw-v1.2.3': (336, 'ed587fc9cf4b95a9b7197f757c7db0b25dee5abeff354e2cef464ca2c18cf45f'),
    'None|False|descriptor_magic|other|fw-v9.0.0': (336, 'ac65f07c5daefbeb5a99f016f5eeded6a8984f0b3a4b3638627a3a4403d0931b'),
    '5000|True|None|default|fw-v1.2.3': (8192, 'c50935a356433eaf99e4d0132690ecbe66c22d3d710afab545da330cc3164bfc'),
    '5000|True|None|default|fw-v9.0.0': (8192, '3355b65491d42ee2fe085cc233453faa5b9a2c49ea71bbb790e1f30bcbdb4276'),
    '5000|True|None|other|fw-v1.2.3': (8192, 'cbd83c5f6c5070927aaaa99a77d0fa507bce8ca7ae21789e7610a5ea9e32f531'),
    '5000|True|None|other|fw-v9.0.0': (8192, 'c0d0c22b26d3b6ec00d92d4f1122a96af1c92a5bb852f4b272fd5d4cce0770b2'),
    '5000|True|digest|default|fw-v1.2.3': (8192, 'b0141c2b89f46c4d99bb2804560e9481678d4c2d149c3fcdc5c45047815a8267'),
    '5000|True|digest|default|fw-v9.0.0': (8192, '9d1804ac996cbeb1b0a036f18152f4f201818734dfba671e70c15fde2b41a58d'),
    '5000|True|digest|other|fw-v1.2.3': (8192, '6ccb199767ba61798d86df9adc34762408c05f38cf6a1143d7fa4d8071e1cecb'),
    '5000|True|digest|other|fw-v9.0.0': (8192, 'f14589655314cfcfb146cee90b3433adb4c18b8134f0d0fd502140ac05d74d66'),
    '5000|True|signature_digest|default|fw-v1.2.3': (8192, '4cebef128bdd2fc90145bdb206d2a9a0e0b2320975520e337c99e666220ec6d9'),
    '5000|True|signature_digest|default|fw-v9.0.0': (8192, 'dbb97004b15189022d06cdc9f06d6205335fd8cdeacdc72315e1b7f53d9cb38d'),
    '5000|True|signature_digest|other|fw-v1.2.3': (8192, 'f1032abe608787772832f9a9e94113d186752cce6af23114f6ddd6a1c15df631'),
    '5000|True|signature_digest|other|fw-v9.0.0': (8192, 'ef16237169452ff7f7cf77096528f33cc59cdc92be703b447f6771b80234f601'),
    '5000|True|truncate|default|fw-v1.2.3': (8092, 'b6d0c82c5e8cd6669702fd448fa12383847db1e643968f6df79f048b89f5a1e4'),
    '5000|True|truncate|default|fw-v9.0.0': (8092, 'ff3ac7407dcba07789ea4313151a1293f9b3b02325f0ff1ce0ce2810da035cb6'),
    '5000|True|truncate|other|fw-v1.2.3': (8092, 'd81388b511a776a1f623b52b60d984040d05690b91580e637c272d0c2e85a370'),
    '5000|True|truncate|other|fw-v9.0.0': (8092, '2470d98d4da861b628fb6943aea6c8c72fb2c87cb28110504b23572602b124cb'),
    '5000|True|unterminated_version|default|fw-v1.2.3': (8192, '1f367473317b9282eb1837dc9186bfc89bda9f71795c5c20aab49eabe0a131e6'),
    '5000|True|unterminated_version|default|fw-v9.0.0': (8192, '1f367473317b9282eb1837dc9186bfc89bda9f71795c5c20aab49eabe0a131e6'),
    '5000|True|unterminated_version|other|fw-v1.2.3': (8192, '267e18929d86f6306029d472f91fb3ca03fc319d307035f361c3c9aa428f852a'),
    '5000|True|unterminated_version|other|fw-v9.0.0': (8192, '267e18929d86f6306029d472f91fb3ca03fc319d307035f361c3c9aa428f852a'),
    '5000|True|magic|default|fw-v1.2.3': (8192, '8a2ade79d39eaec445be597fedbc887dd259367f757e138d492eba9b51f0d0a6'),
    '5000|True|magic|default|fw-v9.0.0': (8192, '19af0b6e3dcdae1c1d8e33e37b67b637f255cacb89db90d6f45561a0e2ac8790'),
    '5000|True|magic|other|fw-v1.2.3': (8192, '655c58a75dfede748b13e5f50e727658a8ab3567f467e5361986f753512354fe'),
    '5000|True|magic|other|fw-v9.0.0': (8192, '6448e779f2da517d4f465aa20cdb2f933f47ba8f792c86c2d088a1e43cf6fc5e'),
    '5000|True|descriptor_magic|default|fw-v1.2.3': (8192, 'e7b25564f90407b7acafc6f0bcdccbe0455864f28a7aa63f1d6cf54d16924cd7'),
    '5000|True|descriptor_magic|default|fw-v9.0.0': (8192, '8bbc76a51f4303d3bbf88941436655a26c57a946c6a0b220dea99a974f035b80'),
    '5000|True|descriptor_magic|other|fw-v1.2.3': (8192, '286b1b5b5b050fb166db00f1df0a137bae69a61af176ae9cc16b322e73e19c1a'),
    '5000|True|descriptor_magic|other|fw-v9.0.0': (8192, '9a835a694a35e0ff2565a274c67526e56d4fe85a1fac9aec2d9409e30c12b385'),
    '5000|False|None|default|fw-v1.2.3': (5008, '6c11940234e1e9c2d91827283c77556bde05ef8c108d385c0d414e30b957aa07'),
    '5000|False|None|default|fw-v9.0.0': (5008, '373342460a58841fff24b0fcafb393e66496376bd4a7b4f447bbbdbb3430d2ad'),
    '5000|False|None|other|fw-v1.2.3': (5008, '6c11940234e1e9c2d91827283c77556bde05ef8c108d385c0d414e30b957aa07'),
    '5000|False|None|other|fw-v9.0.0': (5008, '373342460a58841fff24b0fcafb393e66496376bd4a7b4f447bbbdbb3430d2ad'),
    '5000|False|digest|default|fw-v1.2.3': (5008, 'f1809df0cf4fe81d01907589f435c0a9de2e0e15f8709e16ac9fd05ae594b351'),
    '5000|False|digest|default|fw-v9.0.0': (5008, '42526dc42fd7e02138ec46ecd985b545a91bd7106627ea3d20a7e55b1d440530'),
    '5000|False|digest|other|fw-v1.2.3': (5008, 'f1809df0cf4fe81d01907589f435c0a9de2e0e15f8709e16ac9fd05ae594b351'),
    '5000|False|digest|other|fw-v9.0.0': (5008, '42526dc42fd7e02138ec46ecd985b545a91bd7106627ea3d20a7e55b1d440530'),
    '5000|False|signature_digest|default|fw-v1.2.3': (5008, '6c11940234e1e9c2d91827283c77556bde05ef8c108d385c0d414e30b957aa07'),
    '5000|False|signature_digest|default|fw-v9.0.0': (5008, '373342460a58841fff24b0fcafb393e66496376bd4a7b4f447bbbdbb3430d2ad'),
    '5000|False|signature_digest|other|fw-v1.2.3': (5008, '6c11940234e1e9c2d91827283c77556bde05ef8c108d385c0d414e30b957aa07'),
    '5000|False|signature_digest|other|fw-v9.0.0': (5008, '373342460a58841fff24b0fcafb393e66496376bd4a7b4f447bbbdbb3430d2ad'),
    '5000|False|truncate|default|fw-v1.2.3': (4908, '302005e06ffbd9d556f459d77154af97bb598d75f371ac99713c3420562b23f9'),
    '5000|False|truncate|default|fw-v9.0.0': (4908, '3ac38f3f54e4ad728ef6bf6b32f0a25edc7ce38896608261f02ee1f0a11fbf76'),
    '5000|False|truncate|other|fw-v1.2.3': (4908, '302005e06ffbd9d556f459d77154af97bb598d75f371ac99713c3420562b23f9'),
    '5000|False|truncate|other|fw-v9.0.0': (4908, '3ac38f3f54e4ad728ef6bf6b32f0a25edc7ce38896608261f02ee1f0a11fbf76'),
    '5000|False|unterminated_version|default|fw-v1.2.3': (5008, '8da512129f9d49f6782ab4544a32e97336654d2388251dce3116e1d397d893be'),
    '5000|False|unterminated_version|default|fw-v9.0.0': (5008, '8da512129f9d49f6782ab4544a32e97336654d2388251dce3116e1d397d893be'),
    '5000|False|unterminated_version|other|fw-v1.2.3': (5008, '8da512129f9d49f6782ab4544a32e97336654d2388251dce3116e1d397d893be'),
    '5000|False|unterminated_version|other|fw-v9.0.0': (5008, '8da512129f9d49f6782ab4544a32e97336654d2388251dce3116e1d397d893be'),
    '5000|False|magic|default|fw-v1.2.3': (5008, '29c7e7b33115dddcc5fb6152b5c7e376f86fad24e6646915b110b4c78d348fdd'),
    '5000|False|magic|default|fw-v9.0.0': (5008, '25855af84b2b9f8bd7a63b30b7bf1cb13a5a70eb00acd6046fc6cf06a5cc12ec'),
    '5000|False|magic|other|fw-v1.2.3': (5008, '29c7e7b33115dddcc5fb6152b5c7e376f86fad24e6646915b110b4c78d348fdd'),
    '5000|False|magic|other|fw-v9.0.0': (5008, '25855af84b2b9f8bd7a63b30b7bf1cb13a5a70eb00acd6046fc6cf06a5cc12ec'),
    '5000|False|descriptor_magic|default|fw-v1.2.3': (5008, '7c028d933ce92baacb15834ff7b72f8d33ea5270382aa561b836be0487f267d8'),
    '5000|False|descriptor_magic|default|fw-v9.0.0': (5008, 'e1e7f61d70488ad39f433e01f0f50be60a8c71b55bf6b088d3ba878334894fcd'),
    '5000|False|descriptor_magic|other|fw-v1.2.3': (5008, '7c028d933ce92baacb15834ff7b72f8d33ea5270382aa561b836be0487f267d8'),
    '5000|False|descriptor_magic|other|fw-v9.0.0': (5008, 'e1e7f61d70488ad39f433e01f0f50be60a8c71b55bf6b088d3ba878334894fcd'),
    '2424832|True|None|default|fw-v1.2.3': (2424832, '91ee3e053fd5b8935b55477dbf381c54502a7b2ac356a59c6000df3a8f64ff3c'),
    '2424832|True|truncate|default|fw-v1.2.3': (2424732, 'c88d989d06a436a3f7cae8915504fc382fe42084a61e8e11dadeb65b60716e5c'),
    '2424832|True|digest|default|fw-v1.2.3': (2424832, '73c869b64bdf9677e00360508e027130dcf02c66a446cd10c42085124aa04f11'),
    '2424832|False|None|default|fw-v1.2.3': (2424832, 'a15a2f843213acdb6bfa716329f5599918e79c8dfc86d304230124c5f8eec53b'),
    '2424833|True|None|default|fw-v1.2.3': (2428928, '074c8462d4565e2c673acd6859585a7059635edbd9578193894ed91613cc2b79'),
    '2424833|True|truncate|default|fw-v1.2.3': (2428828, 'd631d5f0915ab1ee65dc4a9772b1b36cc49451378842271e3834055c8d83c63e'),
    '2424833|True|digest|default|fw-v1.2.3': (2428928, '305c9c351d35792c521c2393bf21fb974fcbe5d3d35eafc111597565f57f5711'),
    '2424833|False|None|default|fw-v1.2.3': (2424848, '59d1a15347b135624de224896699c3ad11abe946337a90faab55a918265d52bd'),
    '1118208|True|None|default|fw-v1.2.3': (1118208, 'd735e9e5f9c90ba3b9d8de963b43489e4287b7432ddf37ffc5f7f26c1c5c893f'),
    '1118208|True|truncate|default|fw-v1.2.3': (1118108, '817998e23e1e26894244e16ba04e156b327c325598c2a03beecd901a973cde6f'),
    '1118208|True|digest|default|fw-v1.2.3': (1118208, '4a0870f22f320b1e2285d78a576d808ef9f94f24121d523010719ab5f050047f'),
    '1118208|False|None|default|fw-v1.2.3': (1118208, '7ec4381c56a3ef82fd327ada3f0ae6c32315b51638c42708536dbdd4a83965d9'),
}


def _build(key):
    size, signed, corrupt, modulus, version = key.split("|")
    return fw.build_image(
        version,
        size=None if size == "None" else int(size),
        signed=signed == "True",
        corrupt=None if corrupt == "None" else corrupt,
        modulus=fw.other_modulus() if modulus == "other" else None,
    )


@pytest.mark.parametrize("key", sorted(PINNED))
def test_the_image_bytes_match_the_pinned_digest(key):
    image = _build(key)
    length, digest = PINNED[key]
    assert (len(image), hashlib.sha256(image).hexdigest()) == (length, digest)


def test_the_pinned_matrix_covers_every_corruption_and_the_size_bounds():
    keys = [k.split("|") for k in PINNED]
    assert {k[2] for k in keys} >= {"None", *fw.CORRUPTIONS}
    assert {k[0] for k in keys} >= {"None", "5000", str(0x250000), str(0x250001),
                                    "1118208"}
