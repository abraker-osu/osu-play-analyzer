"""
Creates a data/version.txt file containing verison info
"""
import textwrap
import datetime


if __name__ == '__main__':
    data = datetime.datetime.now()

    # Thanks: https://stackoverflow.com/a/49543168
    contents = textwrap.dedent(
        f"""
        # UTF-8
        #
        # For more details about fixed file info 'ffi' see:
        # http://msdn.microsoft.com/en-us/library/ms646997.aspx
        VSVersionInfo(
            ffi = FixedFileInfo(
                # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
                # Set not needed items to zero 0.
                filevers = ({data.year}, {data.month}, {data.day}, {10000*data.hour + 100*data.minute + data.second}),
                prodvers = ({data.year}, {data.month}, {data.day}, {10000*data.hour + 100*data.minute + data.second}),
                # Contains a bitmask that specifies the valid bits 'flags'r
                mask = 0x3f,
                # Contains a bitmask that specifies the Boolean attributes of the file.
                flags = 0x0,
                # The operating system for which this file was designed.
                # 0x4 - NT and there is no need to change it.
                OS = 0x4,
                # The general type of file.
                # 0x1 - the file is an application.
                fileType = 0x1,
                # The function of the file.
                # 0x0 - the function is not defined for this fileType
                subtype = 0x0,
                # Creation date and time stamp.
                date = (0, 0)
            ),
            kids = [
                StringFileInfo( [
                    StringTable(
                        u'040904B0', [
                            StringStruct(u'CompanyName',      u'abraker95'),
                            StringStruct(u'FileDescription',  u'An analysis tool for osu! beatmaps, replays, scores, and more!'),
                            StringStruct(u'FileVersion',      u'{data.year}.{data.month}.{data.day}.{10000*data.hour + 100*data.minute + data.second}'),
                            StringStruct(u'InternalName',     u'osu-performance-analyzer'),
                            StringStruct(u'OriginalFilename', u'osu-performance-analyzer.exe'),
                            StringStruct(u'ProductName',      u'osu-performance-analyzer'),
                            StringStruct(u'ProductVersion',   u'{data.year}.{data.month}.{data.day}')
                        ]
                    )
                ] ),
                VarFileInfo([ VarStruct(u'Translation', [1033, 1200]) ])
            ]
        )
        """
    )

    with open('data/version.txt', 'w', encoding='utf-8') as f:
        f.write(contents)
